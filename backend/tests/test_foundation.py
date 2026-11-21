"""
Phase 0 Foundation Test Suite
Validates core configuration, database, SSRF protection, rate limiting,
authentication tokens, health endpoints, and LLM structured parsing.
"""
import asyncio
import pytest
from pydantic import BaseModel
from fastapi.testclient import TestClient
from core.config import settings
from core.db import init_db, DatabaseSession
from core.security import SSRFProtection, RateLimiter, SessionIsolationManager
from core.auth import create_access_token, verify_access_token
from core.llm import llm, LLMNotConfigured
from main import app

# TestClient removed to avoid Python 3.14 starlette thread blocking issue on Windows

def test_config_and_db_init():
    """Verify settings are loaded and database creates all tables successfully."""
    assert settings.APP_NAME == "Enterprise AI Automation Suite"
    init_db()
    db = DatabaseSession()
    assert db is not None
    # Check that tables are created
    tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [t["name"] for t in tables]
    assert "p01_leads" in table_names
    assert "p04_invoices" in table_names
    assert "p10_audit_chain" in table_names
    db.close()

def test_ssrf_protection_blocklist():
    """Verify SSRF validator blocks local, loopback, private subnets, and metadata IPs."""
    # Loopback
    is_safe, reason = SSRFProtection.is_safe_url("http://127.0.0.1:8000/internal")
    assert not is_safe
    assert "forbidden" in reason.lower() or "protected" in reason.lower()

    is_safe, reason = SSRFProtection.is_safe_url("http://localhost:8080")
    assert not is_safe

    # Cloud Metadata (AWS/GCP/Azure)
    is_safe, reason = SSRFProtection.is_safe_url("http://169.254.169.254/latest/meta-data/")
    assert not is_safe

    # Invalid scheme
    is_safe, reason = SSRFProtection.is_safe_url("file:///etc/passwd")
    assert not is_safe
    assert "scheme" in reason.lower()

def test_rate_limiter():
    """Verify in-memory sliding window rate limiter."""
    limiter = RateLimiter(limit_per_minute=3)
    test_id = "test_client_99"

    assert limiter.is_allowed(test_id) is True
    assert limiter.is_allowed(test_id) is True
    assert limiter.is_allowed(test_id) is True
    # 4th request must be denied
    assert limiter.is_allowed(test_id) is False

def test_jwt_auth_tokens():
    """Verify HMAC-SHA256 JWT generation and validation."""
    payload = {"sub": "user_42", "role": "admin"}
    token = create_access_token(payload, expires_in_seconds=60)
    assert token is not None
    assert len(token.split('.')) == 3

    verified = verify_access_token(token)
    assert verified["sub"] == "user_42"
    assert verified["role"] == "admin"

def test_session_isolation():
    """Verify ephemeral demo session creation and TTL."""
    manager = SessionIsolationManager(ttl_seconds=3600)
    session = manager.get_or_create_session("sess_abc")
    assert session is not None
    assert "data" in session

    # Retrieve existing
    session["data"]["counter"] = 10
    session2 = manager.get_or_create_session("sess_abc")
    assert session2["data"]["counter"] == 10

from core.health import get_project_health, get_all_projects_health

def test_health_endpoints():
    """Verify dynamic health router returns accurate integration statuses."""
    data = get_project_health("real-estate-sales-agents")
    assert data["slug"] == "real-estate-sales-agents"
    assert "integrations" in data
    assert "uptime_seconds" in data

    # Unknown slug
    data_unknown = get_project_health("unknown-project")
    assert data_unknown["status"] == "error"

    # Fleet summary
    summary = get_all_projects_health()
    assert summary["total_projects"] == 10

class SampleExtraction(BaseModel):
    summary: str
    confidence_score: int
    is_valid: bool

def test_llm_structured_output(monkeypatch):
    """Verify LLM client structured parsing with Pydantic model validation and unconfigured exception."""
    prompt = "Extract summary for verified corporate contract."
    
    # 1. Without API key -> raises LLMNotConfigured
    monkeypatch.setattr(llm, "gemini_key", None)
    monkeypatch.setattr(llm, "openai_key", None)
    with pytest.raises(LLMNotConfigured):
        llm.generate_structured(prompt, SampleExtraction)

    # 2. With mocked provider response -> parses successfully
    monkeypatch.setattr(llm, "gemini_key", "test-key-123")
    monkeypatch.setattr(
        llm,
        "_call_gemini_sync",
        lambda *args, **kwargs: (
            '{"summary": "Verified contract terms", "confidence_score": 98, "is_valid": true}',
            10,
            20
        )
    )
    result = llm.generate_structured(prompt, SampleExtraction)
    assert isinstance(result, SampleExtraction)
    assert result.summary == "Verified contract terms"
    assert result.confidence_score == 98
    assert result.is_valid is True
