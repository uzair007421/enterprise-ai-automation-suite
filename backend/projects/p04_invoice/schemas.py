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
    vendor_name: str = Field(description="Company or contractor issuing the invoice")
    vendor_tax_id: Optional[str] = Field(default=None, description="Tax ID / EIN / VAT number if present")
    invoice_number: str = Field(description="Unique invoice identifier or billing code")
    invoice_date: str = Field(description="Date invoice was issued (YYYY-MM-DD)")
    due_date: Optional[str] = Field(default=None, description="Payment due date (YYYY-MM-DD)")
    currency: str = Field(default="USD", description="Billing currency code (USD, EUR, GBP, PKR, etc.)")
    line_items: List[LineItem] = Field(default_factory=list, description="Extracted line items")
    subtotal: float = Field(description="Subtotal before tax")
    tax_amount: float = Field(default=0.0, description="Stated tax amount")
    total_amount: float = Field(description="Final total billed amount")
    confidence_score: int = Field(default=95, ge=0, le=100, description="OCR extraction confidence (0-100)")

class ReconciliationCheck(BaseModel):
    line_items_vs_subtotal_matched: bool
    line_items_sum: float
    stated_subtotal: float
    subtotal_delta: float
    subtotal_plus_tax_vs_total_matched: bool
    expected_total: float
    stated_total: float
    total_delta: float
    tax_rate_percentage: Optional[float] = None
    discrepancy_details: List[str] = Field(default_factory=list)
    overall_status: str  # "APPROVED" | "DISCREPANCY" | "NEEDS_MANUAL_REVIEW"

class DuplicateCheckResult(BaseModel):
    is_duplicate: bool
    duplicate_match_id: Optional[str] = None
    match_reason: Optional[str] = None

class InvoiceProcessRequest(BaseModel):
    raw_text: Optional[str] = None
    filename: Optional[str] = "invoice.pdf"
    session_id: Optional[str] = "demo_session"
    manual_data: Optional[InvoiceExtractedData] = None

class InvoiceProcessResponse(BaseModel):
    invoice_id: str
    file_sha256: str
    vendor_name: str
    invoice_number: str
    invoice_date: str
    total_amount: float
    currency: str
    confidence_score: int
    extracted: InvoiceExtractedData
    reconciliation: ReconciliationCheck
    duplicate_check: DuplicateCheckResult
    accounting_sync_status: str  # "posted_live" | "queued_sandbox" | "rejected"
    message: str
    execution_time_ms: float
