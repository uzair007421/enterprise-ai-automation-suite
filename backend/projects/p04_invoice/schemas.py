"""
Invoice Processing Pydantic Schemas
Strict data contracts for OCR extraction, 4-way math reconciliation,
duplicate detection, and ERP ledger synchronization.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class LineItem(BaseModel):
    description: str = Field(description="Description of the service or product")
    quantity: float = Field(default=1.0, description="Quantity billed")
    unit_price: float = Field(description="Unit price per item")
    line_total: float = Field(description="Total for this line item (quantity * unit_price)")

class InvoiceExtractedData(BaseModel):
    vendor_name: Optional[str] = Field(default=None, description="Company or contractor issuing the invoice")
    vendor_tax_id: Optional[str] = Field(default=None, description="Tax ID / EIN / VAT number if present")
    invoice_number: Optional[str] = Field(default=None, description="Unique invoice identifier or billing code")
    invoice_date: Optional[str] = Field(default=None, description="Date invoice was issued (YYYY-MM-DD)")
    due_date: Optional[str] = Field(default=None, description="Payment due date (YYYY-MM-DD)")
    currency: str = Field(default="USD", description="Billing currency code (USD, EUR, GBP, PKR, etc.)")
    line_items: List[LineItem] = Field(default_factory=list, description="Extracted line items")
    subtotal: Optional[float] = Field(default=None, description="Subtotal before tax")
    tax_amount: Optional[float] = Field(default=0.0, description="Stated tax amount")
    total_amount: Optional[float] = Field(default=None, description="Final total billed amount")
    confidence_score: int = Field(default=95, ge=0, le=100, description="OCR extraction confidence (0-100)")

class ReconciliationCheck(BaseModel):
    line_items_vs_subtotal_matched: bool
    line_items_sum: Optional[float] = None
    stated_subtotal: Optional[float] = None
    subtotal_delta: Optional[float] = None
    subtotal_plus_tax_vs_total_matched: bool
    expected_total: Optional[float] = None
    stated_total: Optional[float] = None
    total_delta: Optional[float] = None
    tax_rate_percentage: Optional[float] = None
    discrepancy_details: List[str] = Field(default_factory=list)
    overall_status: str  # "APPROVED" | "DISCREPANCY" | "NEEDS_MANUAL_REVIEW" | "NEEDS_REVIEW"

class DuplicateCheckResult(BaseModel):
    is_duplicate: bool
    duplicate_match_id: Optional[str] = None
    match_reason: Optional[str] = None

class InvoiceProcessRequest(BaseModel):
    raw_text: Optional[str] = None
    filename: Optional[str] = "invoice.pdf"
    session_id: Optional[str] = "demo_session"
    manual_data: Optional[InvoiceExtractedData] = None
    tenant_id: str = Field(default="tenant_default", description="Multi-tenant enterprise partition")

class InvoiceProcessResponse(BaseModel):
    invoice_id: str
    tenant_id: str = "tenant_default"
    file_sha256: str
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[float] = None
    currency: str
    confidence_score: int
    extracted: InvoiceExtractedData
    reconciliation: ReconciliationCheck
    duplicate_check: DuplicateCheckResult
    accounting_sync_status: str  # "posted_live" | "queued_sandbox" | "rejected"
    message: str
    execution_time_ms: float
    engine: str = "rules"
