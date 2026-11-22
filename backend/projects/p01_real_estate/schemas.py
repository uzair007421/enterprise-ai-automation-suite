"""
Project 01: Multi-Agent Real Estate Sales Team Schemas
SaaS Multi-Tenant Contracts for Lead Qualification, MLS Matching, Offer Drafting,
and Broker Governance.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class RawLeadInquiry(BaseModel):
    text: str = Field(description="Raw lead inquiry from email, webform, or Zillow/Realtor webhook")
    channel: Optional[str] = "Webform"
    tenant_id: Optional[str] = Field(default="default_brokerage", description="SaaS brokerage partition")
    session_id: Optional[str] = "demo_session"

class QualifiedLead(BaseModel):
    lead_id: str
    tenant_id: str = "default_brokerage"
    name: str
    email: str
    phone: str
    budget: float
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    location: str
    bedrooms: int
    timeline: str
    score: int = Field(ge=0, le=100)
    score_tier: str  # "HOT" | "WARM" | "COLD" | "DISQUALIFIED" | "INCOMPLETE_INQUIRY"
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
    tenant_id: str = "default_brokerage"
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
    tenant_id: str = "default_brokerage"
    engine: str = "rules"
    execution_time_ms: float

class BrokerDecisionRequest(BaseModel):
    offer_id: str
    decision: str = Field(description="'APPROVE', 'MODIFY', or 'REJECT'")
    modified_price: Optional[float] = None
    broker_notes: Optional[str] = "Approved by Managing Broker"
    tenant_id: Optional[str] = "default_brokerage"
    session_id: Optional[str] = "demo_session"

class BrokerDecisionResponse(BaseModel):
    offer_id: str
    tenant_id: str = "default_brokerage"
    status: str
    final_price: float
    broker_notes: str
    dispatched_to_client: bool
    message: str
