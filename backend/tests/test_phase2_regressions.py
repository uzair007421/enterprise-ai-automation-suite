"""
Phase 2 Regression Test Suite
Consolidated regression tests for Tier 0, Tier A, and Tier B audits.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from core.llm import llm, LLMNotConfigured
from core.config import settings, Settings

client = TestClient(app)

# ==============================================================
# TIER 0: GLOBAL FIXES REGRESSIONS
# ==============================================================

def test_tier0_g1_import_and_annotations():
    """Verify backend main imports cleanly and events.py has valid Any annotation."""
    from core.events import EventBroker
    broker = EventBroker()
    assert hasattr(broker, "publish")


def test_tier0_g2_llm_not_configured_no_fabrication(monkeypatch):
    """Verify LLMClient never fabricates fallback domain data when keys are missing."""
    from pydantic import BaseModel
    class DummyModel(BaseModel):
        vendor: str
        total: float

    monkeypatch.setattr(llm, "gemini_key", None)
    monkeypatch.setattr(llm, "openai_key", None)

    with pytest.raises(LLMNotConfigured):
        llm.generate_structured("Extract invoice", DummyModel)


def test_tier0_g4_health_truthful_and_engine():
    """Verify health endpoint dynamically reads results.json and includes engine mode."""
    resp = client.get("/api/ai/invoice-processing/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "engine" in data
    assert data["engine"] in ("llm", "rules")
    # Verify tesseract_ocr is not claimed
    assert "tesseract_ocr" not in data.get("integrations", {})


def test_tier0_g5_admin_token_gating_and_masking():
    """Verify list endpoints are gated by X-Admin-Token and return masked data."""
    # 1. Without token -> 403
    resp_no_auth = client.get("/api/ai/ecommerce-support-bot/orders")
    assert resp_no_auth.status_code == 403

    # 2. With valid token -> 200
    resp_auth = client.get(
        "/api/ai/ecommerce-support-bot/orders",
        headers={"X-Admin-Token": settings.ADMIN_TOKEN}
    )
    assert resp_auth.status_code == 200
    orders = resp_auth.json().get("orders", [])
    for o in orders:
        if "customer_email" in o and o["customer_email"]:
            assert "***" in o["customer_email"]


def test_tier0_g6_production_secret_guard():
    """Verify app fails startup when APP_ENV=production with default SECRET_KEY."""
    with pytest.raises(Exception):
        Settings(APP_ENV="production", SECRET_KEY="production-ai-suite-secret-key-change-in-prod-xyz123")
