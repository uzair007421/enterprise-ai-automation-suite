"""
Data models for Multi-Agent Real Estate Sales System
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

@dataclass
class Lead:
    lead_id: str
    source: str
    name: str
    email: str
    phone: str
    raw_inquiry: str
    budget_min: float
    budget_max: float
    desired_location: str
    bedrooms_needed: int
    timeline: str
    pre_approved: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class QualificationReport:
    lead_id: str
    qualification_status: str  # "HOT", "WARM", "COLD", "DISQUALIFIED"
    score: int  # 0 to 100
    buyer_intent: str
    budget_feasibility: str
    urgency_level: str
    key_strengths: List[str]
    risk_factors: List[str]
    qualifier_notes: str
    recommended_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PropertyMatch:
    property_id: str
    title: str
    price: float
    location: str
    match_score: int  # 0 to 100
    match_reasons: List[str]
    concessions_suggested: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DraftOffer:
    offer_id: str
    lead_id: str
    property_id: str
    headline: str
    proposed_price: float
    incentive_package: str
    formal_offer_letter: str
    whatsapp_teaser: str
    expires_in_days: int = 7

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class WorkflowState:
    lead_id: str
    lead: Lead
    qualification: Optional[QualificationReport] = None
    matched_properties: List[PropertyMatch] = field(default_factory=list)
    draft_offer: Optional[DraftOffer] = None
    status: str = "INTAKE"  # INTAKE, QUALIFIED, MATCHED, DRAFTED, PENDING_HUMAN_APPROVAL, APPROVED, REJECTED, DISPATCHED
    human_feedback: Optional[str] = None
    human_reviewer: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data
