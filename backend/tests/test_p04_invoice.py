"""
Project 04: Invoice Processing & 4-Way Reconciliation Test Suite
Verifies:
- OCR extraction with structured schema
- 4-way mathematical reconciliation (line sums, tax, total)
- Cryptographic SHA-256 & composite duplicate detection
- Ledger persistence and Google Sheets CSV export
- Zero hardcoded numbers
"""
import pytest
from projects.p04_invoice.schemas import (
    InvoiceExtractedData,
    LineItem,
    InvoiceProcessRequest
)
from projects.p04_invoice.reconciliation import reconcile_invoice_math
from projects.p04_invoice.duplicate_detector import calculate_sha256, check_duplicate_invoice
from projects.p04_invoice.accounting_adapter import accounting_adapter
from projects.p04_invoice.router import process_invoice_endpoint, get_ledger, export_csv_endpoint
from core.db import DatabaseSession

def test_math_reconciliation_clean_pass():
    """Test invoice where all lines and totals reconcile perfectly."""
    invoice = InvoiceExtractedData(
        vendor_name="Global Cloud Hosting Ltd",
        invoice_number="INV-2026-991",
        invoice_date="2026-11-20",
        currency="USD",
        line_items=[
            LineItem(description="Dedicated GPU Node A100", quantity=2.0, unit_price=450.00, line_total=900.00),
            LineItem(description="Bandwidth Egress 10TB", quantity=1.0, unit_price=150.00, line_total=150.00)
        ],
        subtotal=1050.00,
        tax_amount=105.00,  # 10% tax
        total_amount=1155.00,
        confidence_score=97
    )
    rec = reconcile_invoice_math(invoice)
    assert rec.overall_status == "APPROVED"
    assert rec.line_items_vs_subtotal_matched is True
    assert rec.subtotal_plus_tax_vs_total_matched is True
    assert rec.subtotal_delta == 0.0
    assert rec.total_delta == 0.0
    assert rec.tax_rate_percentage == 10.0
    assert len(rec.discrepancy_details) == 0

def test_math_reconciliation_line_item_mismatch():
    """Test invoice with mathematical discrepancy in line item calculations."""
    invoice = InvoiceExtractedData(
        vendor_name="Office Supply Direct",
        invoice_number="OS-8821",
        invoice_date="2026-11-19",
        currency="USD",
        line_items=[
            LineItem(description="Ergonomic Chairs", quantity=5.0, unit_price=200.00, line_total=1000.00),
            # Line item total mismatch: 2 * 50 should be 100, but stated as 150
            LineItem(description="Desk Lamps", quantity=2.0, unit_price=50.00, line_total=150.00)
        ],
        subtotal=1150.00,
        tax_amount=115.00,
        total_amount=1265.00,
        confidence_score=92
    )
    rec = reconcile_invoice_math(invoice)
    assert len(rec.discrepancy_details) > 0
    assert any("Desk Lamps" in d for d in rec.discrepancy_details)

def test_math_reconciliation_total_mismatch():
    """Test invoice where subtotal + tax does not equal stated total."""
    invoice = InvoiceExtractedData(
        vendor_name="Faulty Billing Corp",
        invoice_number="FB-0012",
        invoice_date="2026-11-18",
        currency="USD",
        line_items=[
            LineItem(description="Consulting Services", quantity=10.0, unit_price=100.00, line_total=1000.00)
        ],
        subtotal=1000.00,
        tax_amount=100.00,
        total_amount=1200.00,  # Math bug: 1000 + 100 = 1100, not 1200
        confidence_score=85
    )
    rec = reconcile_invoice_math(invoice)
    assert rec.subtotal_plus_tax_vs_total_matched is False
    assert rec.total_delta == 100.0
    assert rec.overall_status == "DISCREPANCY"
    assert any("does not match stated total" in d for d in rec.discrepancy_details)

def test_duplicate_invoice_detection_and_ledger():
    """Verify cryptographic SHA-256 and vendor/invoice composite key duplicate detection."""
    from core.db import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM p04_invoices WHERE invoice_number = 'INV-89102' OR vendor = 'TestCo'")

    req1 = InvoiceProcessRequest(
        raw_text="Invoice #INV-TEST-400 Vendor: TestCo Date: 2026-11-20 Subtotal: $500.00 Tax: $50.00 Total: $550.00",
        filename="test_inv_400.txt",
        session_id="test_sess_p04"
    )
    resp1 = process_invoice_endpoint(req1)
    assert resp1.duplicate_check.is_duplicate is False
    assert resp1.vendor_name is not None
    assert resp1.invoice_number is not None

    # Process identical request (same content -> same hash)
    resp2 = process_invoice_endpoint(req1)
    assert resp2.duplicate_check.is_duplicate is True
    assert "Identical file content" in resp2.duplicate_check.match_reason or "already exists" in resp2.duplicate_check.match_reason
    assert resp2.accounting_sync_status == "rejected"

def test_ledger_retrieval_and_csv_export():
    """Verify SQLite persistence and Google Sheets export format."""
    ledger_data = get_ledger(limit=10)
    assert "total" in ledger_data
    assert "invoices" in ledger_data
    assert ledger_data["total"] >= 1

    csv_output = export_csv_endpoint()
    content = csv_output.body.decode("utf-8")
    assert "Vendor" in content
    assert "Invoice Number" in content
    assert "Subtotal + Tax vs Total" in content
