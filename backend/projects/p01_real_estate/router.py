"""
Project 01: Multi-Agent Real Estate Sales Team Router
Coordinates 3 specialized autonomous agents with Human-in-the-Loop Broker Approval Gate.
"""
import time
import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from core.db import get_db, DatabaseSession
from core.events import event_broker
from .schemas import (
    RawLeadInquiry,
    QualifiedLead,
    PropertyListing,
    DraftOffer,
    LeadPipelineResponse,
    BrokerDecisionRequest,
    BrokerDecisionResponse
)
from .agent_qualifier import qualify_lead_from_text
from .agent_matcher import match_properties_for_lead, MLS_DATABASE
from .agent_drafter import draft_purchase_offer
from .crm_adapter import crm_adapter

router = APIRouter(prefix="/api/ai/real-estate-sales", tags=["P01 Real Estate Sales"])

@router.post("/ingest", response_model=LeadPipelineResponse)
def ingest_lead(inquiry: RawLeadInquiry, db: DatabaseSession = Depends(get_db)):
    """
    Executes the 3-agent autonomous real estate pipeline:
    1. Agent 1: Lead Qualification & Scoring
    2. Agent 2: MLS Property Matching
    3. Agent 3: Policy-bound Purchase Offer Drafting
    Enforces broker gate before any offer can be finalized.
    """
    t_start = time.perf_counter()
    session_id = inquiry.session_id or "demo_session"

    event_broker.publish(session_id, {
        "project": "p01_real_estate",
        "stage": "INGESTION",
        "message": f"Processing incoming buyer inquiry ({len(inquiry.text)} chars)..."
    })

    # Agent 1: Lead Qualification
    lead: QualifiedLead = qualify_lead_from_text(inquiry.text)
    event_broker.publish(session_id, {
        "project": "p01_real_estate",
        "stage": "AGENT_1_QUALIFIED",
        "lead_id": lead.lead_id,
        "score": lead.score,
        "tier": lead.score_tier,
        "message": f"Lead qualified: Score {lead.score}/100 ({lead.score_tier}) - {lead.fit_reason}"
    })

    # Agent 2: MLS Matching
    matches: List[PropertyListing] = match_properties_for_lead(lead)
    event_broker.publish(session_id, {
        "project": "p01_real_estate",
        "stage": "AGENT_2_MATCHED",
        "match_count": len(matches),
        "message": f"MLS Engine identified {len(matches)} matching properties in {lead.location}."
    })

    # Agent 3: Offer Drafting
    draft_offer: Optional[DraftOffer] = None
    if matches and lead.score_tier in ("HOT", "WARM"):
        draft_offer = draft_purchase_offer(lead, matches[0])
        event_broker.publish(session_id, {
            "project": "p01_real_estate",
            "stage": "AGENT_3_DRAFTED",
            "offer_id": draft_offer.offer_id,
            "offered_price": draft_offer.offered_price,
            "status": draft_offer.status,
            "message": f"Draft offer generated: ${draft_offer.offered_price:,.0f} on {draft_offer.mls_id}. HELD for Broker Approval."
        })

    # Persist Lead to Database
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db.execute("""
        INSERT INTO p01_leads (
            id, name, email, phone, budget, location, bedrooms, timeline,
            status, score_tier, fit_reason, raw_inquiry, broker_approved, dispatched, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead.lead_id, lead.name, lead.email, lead.phone, lead.budget,
        lead.location, lead.bedrooms, lead.timeline, "QUALIFIED",
        lead.score_tier, lead.fit_reason, inquiry.text, 0, 0, now_str
    ))

    # Persist Offer if created
    if draft_offer:
        db.execute("""
            INSERT INTO p01_offers (
                id, lead_id, mls_id, property_address, offered_price,
                earnest_deposit, inspection_days, financing_contingency_days,
                broker_approved, status, broker_notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            draft_offer.offer_id, draft_offer.lead_id, draft_offer.mls_id,
            draft_offer.property_address, draft_offer.offered_price,
            draft_offer.earnest_deposit, draft_offer.inspection_days,
            draft_offer.financing_contingency_days, 0, draft_offer.status,
            "Awaiting Broker Review", now_str, now_str
        ))

        # Alert Managing Broker
        crm_adapter.notify_broker_pending_offer(draft_offer.model_dump(), lead.name)

    db.commit()

    # Sync to CRM
    _, hubspot_status = crm_adapter.sync_lead_and_offer(
        lead.model_dump(),
        draft_offer.model_dump() if draft_offer else None
    )

    t_elapsed = (time.perf_counter() - t_start) * 1000.0

    return LeadPipelineResponse(
        lead=lead,
        matched_properties=matches,
        draft_offer=draft_offer,
        broker_action_required=draft_offer is not None,
        hubspot_sync_status=hubspot_status,
        execution_time_ms=round(t_elapsed, 2)
    )

@router.get("/leads")
def get_all_leads(db: DatabaseSession = Depends(get_db)):
    """Fetches all qualified leads and current statuses from SQLite."""
    rows = db.query_all("SELECT * FROM p01_leads ORDER BY created_at DESC LIMIT 50")
    return {"leads": rows, "count": len(rows)}

@router.get("/inventory")
def get_mls_inventory():
    """Returns verified MLS inventory available for matching."""
    return {"properties": MLS_DATABASE, "count": len(MLS_DATABASE)}

@router.post("/broker/decision", response_model=BrokerDecisionResponse)
def execute_broker_decision(req: BrokerDecisionRequest, db: DatabaseSession = Depends(get_db)):
    """
    Human-in-the-Loop Gate: Broker reviews, modifies, approves, or rejects drafted offer.
    """
    row = db.query_one("SELECT * FROM p01_offers WHERE id = ?", (req.offer_id,))
    if not row:
        raise HTTPException(status_code=404, detail=f"Offer {req.offer_id} not found.")

    decision_norm = req.decision.upper().strip()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    session_id = req.session_id or "demo_session"

    final_price = float(row["offered_price"])
    dispatched = False

    if decision_norm == "APPROVE":
        new_status = "BROKER_APPROVED"
        dispatched = True
        msg = f"Offer {req.offer_id} signed off by broker. Dispatched to client for signature."
    elif decision_norm == "MODIFY":
        new_status = "BROKER_MODIFIED"
        if req.modified_price and req.modified_price > 0:
            final_price = req.modified_price
        dispatched = True
        msg = f"Offer {req.offer_id} modified by broker to ${final_price:,.0f} and dispatched."
    elif decision_norm == "REJECT":
        new_status = "BROKER_REJECTED"
        msg = f"Offer {req.offer_id} rejected by broker. Sent back to agent desk."
    else:
        raise HTTPException(status_code=400, detail="Invalid decision. Use 'APPROVE', 'MODIFY', or 'REJECT'.")

    db.execute("""
        UPDATE p01_offers
        SET status = ?, offered_price = ?, broker_approved = ?, broker_notes = ?, updated_at = ?
        WHERE id = ?
    """, (
        new_status, final_price, 1 if dispatched else 0, req.broker_notes or "", now_str, req.offer_id
    ))

    db.execute("""
        UPDATE p01_leads
        SET broker_approved = ?, dispatched = ?
        WHERE id = ?
    """, (1 if dispatched else 0, 1 if dispatched else 0, row["lead_id"]))

    db.commit()

    event_broker.publish(session_id, {
        "project": "p01_real_estate",
        "stage": "BROKER_ACTION_LOGGED",
        "offer_id": req.offer_id,
        "decision": new_status,
        "final_price": final_price,
        "message": msg
    })

    return BrokerDecisionResponse(
        offer_id=req.offer_id,
        status=new_status,
        final_price=final_price,
        broker_notes=req.broker_notes or "",
        dispatched_to_client=dispatched,
        message=msg
    )
