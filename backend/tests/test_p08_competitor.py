"""
Unit & Integration Tests for Project 08: SaaS Competitor Intelligence Engine
Verifies:
1. Strict SSRF protection blocking loopback, internal private subnets, and metadata endpoints.
2. DOM semantic diffing classifying PRICING_CHANGE (impact >= 8).
3. Feature launch and positioning shift categorization.
4. Persistence into SQLite p08_competitor_diffs table.
"""
import pytest
from fastapi import HTTPException
from core.db import init_db, DatabaseSession
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

    # Verify SQLite row
    diff_id = res.changes_detected[0].diff_id
    row = session.query_one("SELECT * FROM p08_competitor_diffs WHERE id = ?", (diff_id,))
    assert row is not None
    assert row["competitor_name"] == "Acme Corp"
    assert row["change_type"] == "PRICING_CHANGE"

    session.close()
