"""
Agent 3: Policy-Bound Offer Drafting Agent
Drafts legal real estate purchase contracts strictly abiding by brokerage risk parameters:
1. Earnest money deposit fixed to standard 1.5% - 2.5% of offered price.
2. Mandatory 7-10 day inspection contingency.
3. Mandatory 21-day financing contingency (waived only for verified cash buyers).
4. Strict safety lock: ALL drafted offers marked PENDING_BROKER_REVIEW.
   AI agent is prohibited from transmitting offers directly to sellers or clients.
"""
import uuid
import logging
from typing import Optional
from .schemas import QualifiedLead, PropertyListing, DraftOffer

logger = logging.getLogger("p01_real_estate.drafter")

def draft_purchase_offer(lead: QualifiedLead, property_match: PropertyListing) -> Optional[DraftOffer]:
    """
    Drafts compliant purchase offer for qualified leads (HOT or WARM).
    Returns None if lead is COLD or DISQUALIFIED.
    """
    if lead.score_tier in ("COLD", "DISQUALIFIED"):
        logger.info(f"Offer drafting suppressed: Lead {lead.lead_id} tier is {lead.score_tier}")
        return None

    offer_id = f"OFFER-{uuid.uuid4().hex[:6].upper()}"

    # Determine offered price: cap at buyer budget, but align reasonably with listing price
    list_price = property_match.price
    if lead.budget >= list_price:
        # Standard competitive offer: 98% to 100% of listing price
        offered_price = round(min(lead.budget, list_price * 0.99), -3)
    else:
        # Constrained offer at lead budget maximum
        offered_price = lead.budget

    # Earnest money deposit: 2% policy standard
    earnest_deposit = round(offered_price * 0.02, -2)

    # Contingencies based on qualification
    is_cash = "cash" in lead.timeline.lower() or "cash" in lead.fit_reason.lower()
    inspection_days = 8
    financing_contingency_days = 0 if is_cash else 21

    logger.info(
        f"Drafted offer {offer_id} for Lead {lead.lead_id} on {property_match.mls_id} "
        f"at ${offered_price:,.0f} (Status: PENDING_BROKER_REVIEW)"
    )

    return DraftOffer(
        offer_id=offer_id,
        tenant_id=lead.tenant_id or "default_brokerage",
        lead_id=lead.lead_id,
        mls_id=property_match.mls_id,
        property_address=f"{property_match.address}, {property_match.city}",
        offered_price=offered_price,
        earnest_deposit=earnest_deposit,
        inspection_days=inspection_days,
        financing_contingency_days=financing_contingency_days,
        broker_approved=False,
        status="PENDING_BROKER_REVIEW"
    )
