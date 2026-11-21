"""
Unit & Integration Tests for Project 09: Media Content Repurposing Engine
Verifies:
1. Multi-platform generation across 4 channels (LinkedIn, Twitter, Newsletter, Dev.to).
2. Brand safety policy guardrail on compliant vs forbidden hype content.
3. Database persistence of all generated social assets.
4. Social publishing action updating SQLite records.
"""
import pytest
from core.db import init_db, DatabaseSession
from projects.p09_media.repurposing_engine import generate_repurposed_assets, check_brand_voice_safety
from projects.p09_media.router import repurpose_content, publish_social_asset
from projects.p09_media.schemas import ContentRepurposeRequest, PublishAssetRequest

def setup_module(module):
    init_db()

def test_multi_platform_asset_generation():
    title = "Distributed SQLite in Autonomous Multi-Agent Architectures"
    transcript = """In this keynote, we discuss how SQLite WAL mode provides ACID transactions across concurrent Python agents. By decoupling orchestration from disk writes, we achieved sub-5ms transaction latency with zero locking contention."""
    assets = generate_repurposed_assets(title, transcript)
    assert len(assets) == 4
    platforms = {a.platform for a in assets}
    assert platforms == {"LINKEDIN", "TWITTER_THREAD", "NEWSLETTER", "DEV_TO"}
    for a in assets:
        assert a.brand_voice_safety_score >= 90
        assert a.policy_cleared is True

def test_brand_voice_safety_guardrail():
    clean_text = "Standard software engineering best practices for building scalable microservices."
    score, cleared = check_brand_voice_safety(clean_text)
    assert score >= 90
    assert cleared is True

    hype_text = "Use this bot to generate 100% guaranteed passive income overnight and replace all developers!"
    score_bad, cleared_bad = check_brand_voice_safety(hype_text)
    assert score_bad < 50
    assert cleared_bad is False

def test_end_to_end_repurpose_and_publish():
    session = DatabaseSession()
    req = ContentRepurposeRequest(
        source_title="Enterprise Event Stream Design",
        source_transcript="Technical discussion regarding Server-Sent Events (SSE) and asyncio broadcast queues.",
        session_id="test_media_session"
    )

    res = repurpose_content(req, db=session)
    assert res.total_assets == 4
    assert res.brand_voice_status == "VERIFIED_SAFE"

    first_asset = res.assets[0]

    # Test Publish action
    pub_req = PublishAssetRequest(
        asset_id=first_asset.asset_id,
        platform=first_asset.platform,
        content=first_asset.content,
        session_id="test_media_session"
    )
    pub_res = publish_social_asset(pub_req, db=session)
    assert pub_res.status in ("LIVE_PUBLISHED", "SANDBOX_PERSISTED")

    # Verify SQLite row
    row = session.query_one("SELECT * FROM p09_assets WHERE id = ?", (first_asset.asset_id,))
    assert row is not None
    assert row["published"] == 1

    session.close()
