"""
Project 09: Media Content Engine Schemas
SaaS Multi-Tenant Contracts for Long-Form Repurposing, Brand Voice Guardrails,
and Social Publishing.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ContentRepurposeRequest(BaseModel):
    source_title: str
    source_transcript: str = Field(description="Raw audio transcript or article markdown")
    target_platforms: Optional[List[str]] = ["LINKEDIN", "TWITTER_THREAD", "NEWSLETTER", "DEV_TO"]
    tenant_id: Optional[str] = Field(default="default_brand", description="SaaS brand workspace partition")
    session_id: Optional[str] = "demo_session"

class RepurposedAsset(BaseModel):
    asset_id: str
    platform: str
    headline: str
    content: str
    char_count: int
    brand_voice_safety_score: int
    policy_cleared: bool

class ContentRepurposeResponse(BaseModel):
    source_title: str
    tenant_id: str = "default_brand"
    engine: str = "rules"
    assets: List[RepurposedAsset]
    total_assets: int
    brand_voice_status: str  # "VERIFIED_SAFE" | "NEEDS_REVISION"
    execution_time_ms: float

class PublishAssetRequest(BaseModel):
    asset_id: str
    platform: str
    content: str
    tenant_id: Optional[str] = Field(default="default_brand", description="SaaS brand partition")
    session_id: Optional[str] = "demo_session"

class PublishAssetResponse(BaseModel):
    asset_id: str
    platform: str
    tenant_id: str = "default_brand"
    engine: str = "rules"
    status: str
    destination_url: Optional[str]
    live: bool
    message: str
