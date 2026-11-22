"""
Project 08: SaaS Competitor Intelligence Schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CompetitorScanRequest(BaseModel):
    competitor_name: str
    target_url: str = Field(description="Competitor pricing or product page URL")
    previous_html_snapshot: Optional[str] = None
    current_html_snapshot: Optional[str] = None
    session_id: Optional[str] = "demo_session"

class CompetitorDiffItem(BaseModel):
    diff_id: str
    competitor_name: str
    change_type: str  # "PRICING_CHANGE" | "FEATURE_LAUNCH" | "POSITIONING_SHIFT" | "DOCS_UPDATE"
    headline: str
    details: str
    impact_score: int = Field(ge=1, le=10)
    source_url: str
    detected_at: str

class CompetitorScanResponse(BaseModel):
    competitor_name: str
    target_url: str
    ssrf_validated: bool
    changes_detected: List[CompetitorDiffItem]
    diff_count: int = 0
    max_impact_score: int
    recommended_action: str
    execution_time_ms: float
