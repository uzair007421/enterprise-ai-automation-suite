"""
Project 09: Media Content Engine Router
FastAPI router for multi-platform repurposing, brand safety auditing, and verified social publishing.
SaaS Multi-Tenant Partitioning, Honest Publishing Status, and Buzzword Hygiene.
"""
import time
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
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
    Validates against brand voice safety guardrail and saves assets to database partitioned by tenant_id.
    """
    t_start = time.perf_counter()
    session_id = req.session_id or "demo_session"
    tenant_id = req.tenant_id or "default_brand"

    event_broker.publish(session_id, {
        "project": "p09_media",
        "stage": "TRANSCRIPT_INGESTION",
        "title": req.source_title,
        "message": f"Processing source material for workspace [{tenant_id}]: '{req.source_title}' ({len(req.source_transcript)} chars)..."
    })

    assets = generate_repurposed_assets(req.source_title, req.source_transcript)
    all_cleared = all(a.policy_cleared for a in assets)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Save generated assets into Database with tenant_id
    for a in assets:
        db.execute("""
            INSERT INTO p09_assets (
                id, tenant_id, video_title, asset_type, platform, content, approved, published, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            a.asset_id, tenant_id, req.source_title, a.headline, a.platform, a.content, 0, 0, now_str
        ))
    db.commit()

    brand_status = "VERIFIED_SAFE" if all_cleared else "NEEDS_REVISION"

    event_broker.publish(session_id, {
        "project": "p09_media",
        "stage": "ASSETS_GENERATED",
        "asset_count": len(assets),
        "status": brand_status,
        "message": f"Generated {len(assets)} multi-platform assets. Policy Status: {brand_status}."
    })

    t_elapsed = (time.perf_counter() - t_start) * 1000.0

    return ContentRepurposeResponse(
        source_title=req.source_title,
        tenant_id=tenant_id,
        engine="rules",
        assets=assets,
        total_assets=len(assets),
        brand_voice_status=brand_status,
        execution_time_ms=round(t_elapsed, 2)
    )

@router.post("/publish", response_model=PublishAssetResponse)
def publish_social_asset(req: PublishAssetRequest, db: DatabaseSession = Depends(get_db)):
    """
    Publishes an approved asset to target platform via API adapter or returns honest not_configured status.
    """
    session_id = req.session_id or "demo_session"
    tenant_id = req.tenant_id or "default_brand"
    success, status_tag, url, live = social_adapter.publish_asset(req.platform, req.content)

    if not success:
        raise HTTPException(status_code=502, detail=f"Publishing failed: {status_tag}")

    # Update asset in database
    db.execute("""
        UPDATE p09_assets
        SET approved = 1, published = ?
        WHERE id = ? AND (tenant_id = ? OR tenant_id = 'default_brand')
    """, (1 if live else 0, req.asset_id, tenant_id))
    db.commit()

    # Honest user-facing messaging
    if live:
        msg = f"Successfully published to {req.platform} (live=True)."
    else:
        msg = f"Staged draft: {req.platform} credentials not configured (live=False). Live posting requires platform API keys."

    event_broker.publish(session_id, {
        "project": "p09_media",
        "stage": "ASSET_PUBLISHED",
        "asset_id": req.asset_id,
        "platform": req.platform,
        "status": status_tag,
        "url": url,
        "live": live,
        "message": msg
    })

    return PublishAssetResponse(
        asset_id=req.asset_id,
        platform=req.platform,
        tenant_id=tenant_id,
        engine="rules",
        status=status_tag,
        destination_url=url,
        live=live,
        message=msg
    )

@router.get("/assets")
def get_all_assets(
    tenant_id: Optional[str] = Query(default=None, description="Filter assets by workspace tenant partition"),
    db: DatabaseSession = Depends(get_db)
):
    """Retrieves all generated social media assets with tenant filtering."""
    if tenant_id:
        rows = db.fetchall("SELECT * FROM p09_assets WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 50", (tenant_id,))
    else:
        rows = db.fetchall("SELECT * FROM p09_assets ORDER BY created_at DESC LIMIT 50")
    return {"assets": rows, "count": len(rows), "tenant_id": tenant_id}
