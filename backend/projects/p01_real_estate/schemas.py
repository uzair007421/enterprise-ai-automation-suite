"""
Project 01: Multi-Agent Real Estate Sales Team Schemas
Strict contracts for 3-agent pipeline: Lead Qualifier -> Property Matcher -> Offer Drafter -> Broker Desk.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class RawLeadInquiry(BaseModel):
    text: str = Field(description="Raw lead inquiry from email, webform, or Zillow/Realtor webhook")
    channel: Optional[str] = "Webform"
    session_id: Optional[str] = "demo_session"

class QualifiedLead(BaseModel):
    lead_id: str
    name: str
    email: str
    phone: str
    budget: float
    location: str
    bedrooms: int
    timeline: str
    score: int = Field(ge=0, le=100)
    score_tier: str  # "HOT" | "WARM" | "COLD" | "DISQUALIFIED"
    fit_reason: str

class PropertyListing(BaseModel):
    mls_id: str
    address: str
    city: str
    price: float
    bedrooms: int
    bathrooms: float
    sqft: int
    match_score: int
    match_notes: str

class DraftOffer(BaseModel):
    offer_id: str
    lead_id: str
    mls_id: str
    property_address: str
    offered_price: float
    earnest_deposit: float
    inspection_days: int
    financing_contingency_days: int
    broker_approved: bool = False
    status: str  # "PENDING_BROKER_REVIEW" | "BROKER_APPROVED" | "MODIFIED" | "REJECTED"

class LeadPipelineResponse(BaseModel):
    lead: QualifiedLead
    matched_properties: List[PropertyListing]
    draft_offer: Optional[DraftOffer] = None
    broker_action_required: bool
    hubspot_sync_status: str
    execution_time_ms: float

class BrokerDecisionRequest(BaseModel):
    offer_id: str
    decision: str = Field(description="'APPROVE', 'MODIFY', or 'REJECT'")
    modified_price: Optional[float] = None
    broker_notes: Optional[str] = "Approved by Managing Broker"
    session_id: Optional[str] = "demo_session"

class BrokerDecisionResponse(BaseModel):
    offer_id: str
    status: str
    final_price: float
    broker_notes: str
    dispatched_to_client: bool
    message: str
