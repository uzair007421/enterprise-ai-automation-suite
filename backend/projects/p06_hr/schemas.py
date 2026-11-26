"""
Project 06: HR AI Recruiter Assistant Schemas
SaaS Multi-Tenant Contracts for Blind Demographic Screening, Rubric Evaluation, and Interview Scheduling.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class CandidateScreenRequest(BaseModel):
    raw_cv_text: str = Field(description="Raw unstructured resume or CV text")
    job_role: Optional[str] = "Senior Full-Stack / AI Engineer"
    tenant_id: Optional[str] = Field(default="default_company", description="SaaS organization / company partition")
    session_id: Optional[str] = "demo_session"

class PIIAuditReport(BaseModel):
    redacted_tokens_count: int
    categories_redacted: List[str]
    is_fully_anonymized: bool
    residual_categories: List[str] = Field(default_factory=list)

class RubricBreakdown(BaseModel):
    technical_skills: int = Field(ge=0, le=40, description="Core programming languages, frameworks, AI SDKs")
    system_architecture: int = Field(ge=0, le=30, description="Distributed systems, databases, cloud, scaling")
    impact_and_metrics: int = Field(ge=0, le=30, description="Quantified business results, latency, revenue")
    total_score: int = Field(ge=0, le=100)

class CandidateScreenResponse(BaseModel):
    candidate_id: str
    tenant_id: str = "default_company"
    engine: str = "rules"
    anonymized_cv: str
    pii_audit: PIIAuditReport
    rubric: RubricBreakdown
    recommendation: str  # "ADVANCE_TO_INTERVIEW" | "HOLD_FOR_REVIEW" | "REJECT"
    strengths: List[str]
    growth_areas: List[str]
    scheduled_slot: Optional[str] = None
    execution_time_ms: float
