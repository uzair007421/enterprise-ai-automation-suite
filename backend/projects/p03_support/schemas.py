"""
Project 03: Bilingual E-Commerce Support Schemas
Strict contracts for intent classification, multilingual Roman Urdu/Urdu processing,
code-level refund guardrails, and human escalation tickets.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class CustomerMessageRequest(BaseModel):
    session_id: str = Field(default="demo_customer_1", description="Unique session or phone identifier")
    text: str = Field(description="Customer's message in English, Urdu, or Roman Urdu")
    phone: Optional[str] = Field(default=None, description="Customer phone number")
    email: Optional[str] = Field(default=None, description="Customer email address if provided")
    customer_name: Optional[str] = Field(default="Customer", description="Customer name if known")
    tenant_id: str = Field(default="tenant_default", description="Multi-tenant store/workspace partition")

class OrderIngestRequest(BaseModel):
    id: str = Field(description="Order ID e.g. #1045 or 1045")
    customer_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total_usd: float
    status: str = "In Transit"
    courier: str = "TCS Express"
    tracking_id: str
    tenant_id: str = "tenant_default"

class ClassificationResult(BaseModel):
    language: str = Field(description="'English', 'Urdu', or 'Roman Urdu'")
    intent: str = Field(
        description="One of: 'GREETING', 'TRACK_ORDER', 'CANCEL_ORDER', 'RETURN_REQUEST', "
                    "'REFUND_INQUIRY', 'PRODUCT_QUESTION', 'COMPLAINT', 'HUMAN_AGENT', 'OTHER'"
    )
    sentiment: str = Field(description="One of: 'POSITIVE', 'NEUTRAL', 'FRUSTRATED', 'ANGRY'")
    sentiment_score: int = Field(ge=0, le=100, description="0=happy/friendly, 50=neutral, 100=extreme anger")
    is_angry_escalation: bool = Field(description="True if customer is angry or demanding escalation")
    extracted_order_id: Optional[str] = Field(default=None, description="Extracted order ID (e.g. #1042)")
    extracted_tracking_id: Optional[str] = Field(default=None, description="Courier tracking number")
    reasoning: Optional[str] = Field(default=None, description="Brief semantic explanation")
    engine: str = Field(default="rules", description="'llm' or 'rules'")

class BotResponse(BaseModel):
    session_id: str
    reply_text: str
    language: str
    intent: str
    sentiment: str
    sentiment_score: int
    escalated_to_human: bool
    ticket_id: Optional[str] = None
    order_data: Optional[Dict[str, Any]] = None
    refund_blocked: bool = False
    refund_block_reason: Optional[str] = None
    execution_time_ms: float
    engine: str = Field(default="rules", description="'llm' or 'rules'")
    tenant_id: str = Field(default="tenant_default", description="Partition ID")
