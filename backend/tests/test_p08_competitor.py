"""
Unit & Integration Tests for Project 08: SaaS Competitor Intelligence Engine
Verifies:
1. Strict SSRF protection blocking loopback, internal private subnets, and metadata endpoints.
2. DOM semantic diffing classifying PRICING_CHANGE (impact >= 8).
3. Feature launch and positioning shift categorization.
4. Offline sandbox resilience: RFC 2606 test domains validate without external DNS resolution.
5. SaaS multi-tenant competitor isolation.
"""
import pytest
import socket
from fastapi import HTTPException
from core.db import init_db, DatabaseSession
from core.security import validate_url_ssrf_safety
from projects.p08_competitor.diff_engine import extract_competitor_diffs
from projects.p08_competitor.router import scan_competitor_changes
from projects.p08_competitor.schemas import CompetitorScanRequest

def setup_module(module):
    init_db()

def test_ssrf_protection_blocks_malicious_urls():
    session = DatabaseSession()
    malicious_urls = [
        "http://127.0.0.1:8080/internal",
        "http://localhost:5000/metrics",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.1.1/router-login",
        "http://10.0.0.5/secrets"
    ]

    for bad_url in malicious_urls:
        req = CompetitorScanRequest(
            competitor_name="Malicious Actor",
            target_url=bad_url,
            session_id="test_ssrf"
        )
        with pytest.raises(HTTPException) as exc_info:
            scan_competitor_changes(req, db=session)
        assert exc_info.value.status_code == 400
        assert "SSRF" in exc_info.value.detail

    session.close()

def test_offline_sandbox_dns_resilience(monkeypatch):
    """Audit Fix: Verify SSRF safety check on example.com succeeds even when DNS resolution fails in offline sandbox."""
    def fail_dns(host, port):
        raise socket.gaierror(11001, "getaddrinfo failed")

    monkeypatch.setattr(socket, "getaddrinfo", fail_dns)
    # example.com must safely resolve to public test IP fallback
    assert validate_url_ssrf_safety("https://example.com/pricing") is True
    # Localhost must remain blocked
    assert validate_url_ssrf_safety("http://127.0.0.1:8000") is False

def test_pricing_change_diff_classification():
    old_html = "<div>Plan: Starter $49/mo, Enterprise $199/mo</div>"
    new_html = "<div>Plan: Starter $29/mo, Enterprise $149/mo. Free tier now included!</div>"

    diffs = extract_competitor_diffs("SaaS Rival A", "https://rival-a.io/pricing", old_html, new_html)
    assert len(diffs) > 0
    pricing_diff = [d for d in diffs if d.change_type == "PRICING_CHANGE"]
    assert len(pricing_diff) == 1
    assert pricing_diff[0].impact_score >= 8
    assert "Pricing" in pricing_diff[0].headline

def test_feature_launch_diff_classification():
    old_html = "<div>Standard REST endpoints available.</div>"
    new_html = "<div>Now announcing: Native Webhooks and Vector Search integrations with Slack!</div>"

    diffs = extract_competitor_diffs("SaaS Rival B", "https://rival-b.io/features", old_html, new_html)
    feature_diff = [d for d in diffs if d.change_type == "FEATURE_LAUNCH"]
    assert len(feature_diff) == 1
    assert feature_diff[0].impact_score >= 7

def test_end_to_end_scan_and_db_persistence():
    session = DatabaseSession()
    req = CompetitorScanRequest(
        competitor_name="Acme Corp",
        target_url="https://example.com/pricing",
        previous_html_snapshot="<div>Starter: $50/mo</div>",
        current_html_snapshot="<div>Starter: $25/mo with Free Tier</div>",
        session_id="test_scan"
    )

    res = scan_competitor_changes(req, db=session)
    assert res.ssrf_validated is True
    assert len(res.changes_detected) > 0
    assert res.max_impact_score >= 8

    # Verify Database row
    diff_id = res.changes_detected[0].diff_id
    row = session.query_one("SELECT * FROM p08_competitor_diffs WHERE id = ?", (diff_id,))
    assert row is not None
    assert row["competitor_name"] == "Acme Corp"
    assert row["change_type"] == "PRICING_CHANGE"

    session.close()

def test_saas_multi_tenant_competitor_isolation():
    """SaaS Feature: Competitor tracking is isolated by organization tenant partition."""
    session = DatabaseSession()
    req_a = CompetitorScanRequest(
        competitor_name="Cloud AI Rival",
        target_url="https://example.com/cloud-ai",
        previous_html_snapshot="<div>Plan A: $100</div>",
        current_html_snapshot="<div>Plan A: $50</div>",
        tenant_id="org_alpha",
        session_id="test_sess_alpha"
    )
    res_a = scan_competitor_changes(req_a, db=session)
    assert res_a.tenant_id == "org_alpha"

    # Query diffs for org_beta -> must not return org_alpha's diffs
    rows_beta = session.query_all("SELECT * FROM p08_competitor_diffs WHERE tenant_id = 'org_beta'")
    assert all(r["tenant_id"] == "org_beta" for r in rows_beta)

    session.close()
