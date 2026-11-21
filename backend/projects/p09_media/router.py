"""
Project 09: Media Content Engine Router
FastAPI router for multi-platform repurposing, brand safety auditing, and verified social publishing.
"""
import time
import datetime
from fastapi import APIRouter, Depends, HTTPException
from core.db import get_db, DatabaseSession
from core.events import event_broker
from .schemas import (
    ContentRepurposeRequest,
    ContentRepurposeResponse,
    PublishAssetRequest,
    PublishAssetResponse
)
from .repurposing_engine import generate_repurposed_assets
from .social_adapters import social_adapter

router = APIRouter(prefix="/api/ai/media-engine", tags=["P09 Media Content Engine"])

@router.post("/repurpose", response_model=ContentRepurposeResponse)
def repurpose_content(req: ContentRepurposeRequest, db: DatabaseSession = Depends(get_db)):
    """
    Transforms transcript into 4 tailored platform formats (LinkedIn, Twitter Thread, Newsletter, Dev.to).
    Validates against brand voice safety guardrail and saves assets to SQLite.
    """
    t_start = time.perf_counter()
    session_id = req.session_id or "demo_session"

    event_broker.publish(session_id, {
        "project": "p09_media",
        "stage": "TRANSCRIPT_INGESTION",
        "title": req.source_title,
        "message": f"Processing source material: '{req.source_title}' ({len(req.source_transcript)} chars)..."
    })

    assets = generate_repurposed_assets(req.source_title, req.source_transcript)
    all_cleared = all(a.policy_cleared for a in assets)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Save generated assets into SQLite
    for a in assets:
        db.execute("""
            INSERT INTO p09_assets (
                id, video_title, asset_type, platform, content, approved, published, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            a.asset_id, req.source_title, a.headline, a.platform, a.content, 0, 0, now_str
        ))
    db.commit()

    event_broker.publish(session_id, {
        "project": "p09_media",
        "stage": "ASSETS_GENERATED",
        "asset_count": len(assets),
        "status": "VERIFIED_SAFE" if all_cleared else "NEEDS_REVISION",
        "message": f"Generated {len(assets)} multi-platform assets. Policy Status: {'VERIFIED_SAFE' if all_cleared else 'NEEDS_REVISION'}."
    })

    t_elapsed = (time.perf_counter() - t_start) * 1000.0

    return ContentRepurposeResponse(
        source_title=req.source_title,
        assets=assets,
        total_assets=len(assets),
        brand_voice_status="VERIFIED_SAFE" if all_cleared else "NEEDS_REVISION",
        execution_time_ms=round(t_elapsed, 2)
    )

@router.post("/publish", response_model=PublishAssetResponse)
def publish_social_asset(req: PublishAssetRequest, db: DatabaseSession = Depends(get_db)):
    """
    Publishes an approved asset to target platform via API adapter or sandbox.
    """
    session_id = req.session_id or "demo_session"
    success, status_tag, url = social_adapter.publish_asset(req.platform, req.content)

    if not success:
        raise HTTPException(status_code=502, detail=f"Publishing failed: {status_tag}")

    # Update asset in database
    db.execute("""
        UPDATE p09_assets
        SET approved = 1, published = 1
        WHERE id = ?
    """, (req.asset_id,))
    db.commit()

    event_broker.publish(session_id, {
        "project": "p09_media",
        "stage": "ASSET_PUBLISHED",
        "asset_id": req.asset_id,
        "platform": req.platform,
        "status": status_tag,
        "url": url,
        "message": f"Asset {req.asset_id} published to {req.platform} ({status_tag})."
    })

    return PublishAssetResponse(
        asset_id=req.asset_id,
        platform=req.platform,
        status=status_tag,
        destination_url=url,
        message=f"Successfully processed publishing to {req.platform}."
    )

@router.get("/assets")
def get_all_assets(db: DatabaseSession = Depends(get_db)):
    """Fetches all repurposed assets from SQLite."""
    rows = db.fetchall("SELECT * FROM p09_assets ORDER BY created_at DESC LIMIT 50")
    return {"assets": rows, "count": len(rows)}
