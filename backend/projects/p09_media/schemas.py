"""
Project 09: Media Content Engine Schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ContentRepurposeRequest(BaseModel):
    source_title: str
    source_transcript: str = Field(description="Raw video transcript or blog text")
    tone: Optional[str] = "Thought-Leadership & Engineering Rigor"
    session_id: Optional[str] = "demo_session"

class RepurposedAsset(BaseModel):
    asset_id: str
    platform: str  # "LINKEDIN" | "TWITTER_THREAD" | "NEWSLETTER" | "DEV_TO"
    headline: str
    content: str
    estimated_reading_time_sec: int
    brand_voice_safety_score: int = Field(ge=0, le=100)
    policy_cleared: bool

class ContentRepurposeResponse(BaseModel):
    source_title: str
    assets: List[RepurposedAsset]
    total_assets: int
    brand_voice_status: str  # "VERIFIED_SAFE" | "NEEDS_REVISION"
    execution_time_ms: float

class PublishAssetRequest(BaseModel):
    asset_id: str
    platform: str
    content: str
    session_id: Optional[str] = "demo_session"

class PublishAssetResponse(BaseModel):
    asset_id: str
    platform: str
    status: str  # "LIVE_PUBLISHED" | "SANDBOX_PERSISTED" | "not_configured"
    destination_url: Optional[str] = None
    message: str
    live: bool = False
