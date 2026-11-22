"""
Project 08: SaaS Competitor Intelligence Router
FastAPI router for SSRF-safe competitor crawling, DOM diffing, and strategic impact analysis.
"""
import time
import datetime
from fastapi import APIRouter, Depends, HTTPException
from core.db import get_db, DatabaseSession
from core.events import event_broker
from core.security import validate_url_ssrf_safety
from .schemas import (
    CompetitorScanRequest,
    CompetitorScanResponse,
    CompetitorDiffItem
)
from .diff_engine import extract_competitor_diffs
from .crawler import fetch_competitor_html_safe

router = APIRouter(prefix="/api/ai/competitor-intel", tags=["P08 SaaS Competitor Intelligence"])

@router.post("/scan", response_model=CompetitorScanResponse)
def scan_competitor_changes(req: CompetitorScanRequest, db: DatabaseSession = Depends(get_db)):
    """
    Performs SSRF-validated competitor intelligence scan:
    1. Validates destination host safety (blocking private IPs & cloud metadata)
    2. Computes semantic DOM diff against baseline snapshot
    3. Categorizes changes (PRICING_CHANGE, FEATURE_LAUNCH, etc.) and scores strategic impact (1-10)
    4. Persists findings into SQLite
    """
    t_start = time.perf_counter()
    session_id = req.session_id or "demo_session"

    event_broker.publish(session_id, {
        "project": "p08_competitor",
        "stage": "SECURITY_CHECK",
        "url": req.target_url,
        "message": f"Validating SSRF safety for target URL '{req.target_url}'..."
    })

    # SSRF Gate
    if not validate_url_ssrf_safety(req.target_url):
        event_broker.publish(session_id, {
            "project": "p08_competitor",
            "stage": "SSRF_BLOCKED",
            "url": req.target_url,
            "message": "SSRF violation blocked! Host resolved to protected private/metadata address."
        })
        raise HTTPException(
            status_code=400,
            detail="SSRF Security Violation: Target URL resolves to a prohibited private/internal address"
        )

    # Determine HTML snapshots (either provided in request or fetched from DB / web)
    old_html = req.previous_html_snapshot
    new_html = req.current_html_snapshot

    if not new_html:
        success, fetched = fetch_competitor_html_safe(req.target_url)
        if not success:
            t_elapsed = (time.perf_counter() - t_start) * 1000.0
            return CompetitorScanResponse(
                competitor_name=req.competitor_name,
                target_url=req.target_url,
                ssrf_validated=True,
                changes_detected=[],
                diff_count=0,
                max_impact_score=0,
                recommended_action=f"SCRAPE_FAILED: {fetched}",
                execution_time_ms=round(t_elapsed, 2)
            )
        new_html = fetched

    # If previous snapshot was not explicitly provided in the request, look up existing snapshot in DB
    is_initial_baseline = False
    if old_html is None:
        row = db.fetchone("SELECT html_snapshot FROM p08_snapshots WHERE url = ?", (req.target_url,))
        if row and row["html_snapshot"]:
            old_html = row["html_snapshot"]
        else:
            # First scan for this target URL: establish baseline!
            is_initial_baseline = True
            old_html = new_html

    # Save or update latest snapshot in p08_snapshots
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute("""
        INSERT INTO p08_snapshots (url, competitor_name, html_snapshot, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            competitor_name = excluded.competitor_name,
            html_snapshot = excluded.html_snapshot,
            updated_at = excluded.updated_at
    """, (req.target_url, req.competitor_name, new_html, now_str))
    db.commit()

    if is_initial_baseline:
        t_elapsed = (time.perf_counter() - t_start) * 1000.0
        return CompetitorScanResponse(
            competitor_name=req.competitor_name,
            target_url=req.target_url,
            ssrf_validated=True,
            changes_detected=[],
            diff_count=0,
            max_impact_score=0,
            recommended_action="BASELINE_ESTABLISHED: Initial snapshot saved for monitoring. No prior changes to compare.",
            execution_time_ms=round(t_elapsed, 2)
        )

    # Extract Diffs
    diffs = extract_competitor_diffs(req.competitor_name, req.target_url, old_html, new_html)
    max_impact = max([d.impact_score for d in diffs], default=0)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Persist in SQLite
    for d in diffs:
        db.execute("""
            INSERT INTO p08_competitor_diffs (
                id, competitor_name, change_type, headline, details, impact_score, source_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d.diff_id, d.competitor_name, d.change_type, d.headline, d.details,
            d.impact_score, d.source_url, now_str
        ))
    db.commit()

    # Strategic Recommendation
    if max_impact >= 8:
        action = "URGENT COUNTER-MEASURE: Schedule executive product/pricing review to defend market share."
    elif max_impact >= 5:
        action = "MONITOR: Update competitive battlecards and sales enablement playbooks."
    else:
        action = "LOGGED: Routine maintenance copy update. No strategic response required."

    event_broker.publish(session_id, {
        "project": "p08_competitor",
        "stage": "DIFF_ANALYSIS",
        "changes_count": len(diffs),
        "max_impact": max_impact,
        "message": f"Identified {len(diffs)} shifts. Max Impact: {max_impact}/10 ({action[:35]}...)."
    })

    t_elapsed = (time.perf_counter() - t_start) * 1000.0

    return CompetitorScanResponse(
        competitor_name=req.competitor_name,
        target_url=req.target_url,
        ssrf_validated=True,
        changes_detected=diffs,
        diff_count=len(diffs),
        max_impact_score=max_impact,
        recommended_action=action,
        execution_time_ms=round(t_elapsed, 2)
    )

@router.get("/diffs")
def get_recent_diffs(db: DatabaseSession = Depends(get_db)):
    """Retrieves all tracked competitor intelligence shifts from SQLite."""
    rows = db.fetchall("SELECT * FROM p08_competitor_diffs ORDER BY created_at DESC LIMIT 50")
    return {"diffs": rows, "count": len(rows)}
