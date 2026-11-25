"""
Project 04: Invoice Processing & 4-Way Reconciliation Test Suite
Verifies:
- OCR extraction with structured schema & regression protections
- 4-way mathematical reconciliation (line sums, tax, total)
- SHA-256 & composite duplicate detection
- Tenant isolation via signed JWT Bearer auth & X-Session-ID sandbox
- Honest QuickBooks live mode (never returns posted_live without real HTTP 2xx)
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from core.auth import create_access_token
from core.config import settings
from core.db import get_connection
from projects.p04_invoice.schemas import (
    InvoiceExtractedData,
    LineItem,
)
from projects.p04_invoice.reconciliation import reconcile_invoice_math
from projects.p04_invoice.duplicate_detector import calculate_sha256
from projects.p04_invoice.ocr_engine import parse_text_heuristics
from projects.p04_invoice.accounting_adapter import AccountingAdapter

client = TestClient(app)


def _auth_headers(tenant_id: str) -> dict:
    token = create_access_token({"sub": f"user_{tenant_id}", "tenant_id": tenant_id})
    return {"Authorization": f"Bearer {token}"}


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
        total_amount=1200.00,
        confidence_score=85
    )
    rec = reconcile_invoice_math(invoice)
    assert rec.subtotal_plus_tax_vs_total_matched is False
    assert rec.total_delta == 100.0
    assert rec.overall_status == "DISCREPANCY"
    assert any("does not match stated total" in d for d in rec.discrepancy_details)


def test_duplicate_invoice_detection_and_ledger():
    """Verify SHA-256 duplicate detection, ledger read, and CSV export via authenticated HTTP."""
    req_text = "Invoice #INV-TEST-400 Vendor: TestCo Date: 2026-11-20 Subtotal: $500.00 Tax: $50.00 Total: $550.00"
    file_hash = calculate_sha256(req_text.encode("utf-8"))
    with get_connection() as conn:
        conn.execute("DELETE FROM p04_invoices WHERE invoice_number = 'INV-TEST-400' OR vendor = 'TestCo' OR file_hash = ?", (file_hash,))

    headers = _auth_headers("tenant_test_ledger")
    resp1 = client.post(
        "/api/ai/invoice-processing/process",
        headers=headers,
        json={"raw_text": req_text, "filename": "test_inv_400.txt", "session_id": "test_sess_p04"}
    )
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["duplicate_check"]["is_duplicate"] is False
    assert d1["vendor_name"] == "TestCo"
    assert d1["invoice_number"] == "INV-TEST-400"

    resp2 = client.post(
        "/api/ai/invoice-processing/process",
        headers=headers,
        json={"raw_text": req_text, "filename": "test_inv_400.txt", "session_id": "test_sess_p04"}
    )
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["duplicate_check"]["is_duplicate"] is True
    assert d2["accounting_sync_status"] == "rejected"


def test_ledger_retrieval_and_csv_export():
    """Verify authenticated ledger retrieval, CSV export, and 401 when unauthenticated."""
    # Unauthenticated GET /ledger without X-Session-ID must fail with 401 (no cross-visitor leakage)
    unauth = client.get("/api/ai/invoice-processing/ledger")
    assert unauth.status_code == 401

    headers = _auth_headers("tenant_test_ledger")
    ledger_resp = client.get("/api/ai/invoice-processing/ledger?limit=10", headers=headers)
    assert ledger_resp.status_code == 200
    ledger_data = ledger_resp.json()
    assert ledger_data["total"] >= 1

    csv_resp = client.get("/api/ai/invoice-processing/export/csv", headers=headers)
    assert csv_resp.status_code == 200
    content = csv_resp.text
    assert "Vendor" in content
    assert "Invoice Number" in content
    assert "Subtotal + Tax vs Total" in content


def test_saas_multitenant_duplicate_isolation():
    """Verify Company A's invoice #INV-8800 does not block Company B (identity derived from JWT)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM p04_invoices WHERE tenant_id IN ('tenant_company_alpha', 'tenant_company_beta')")

    payload = {
        "raw_text": "Invoice #INV-8800 Vendor: TechFlow Date: 2026-11-20 Subtotal: $1000.00 Tax: $100.00 Total: $1100.00",
        "filename": "inv.txt",
        "session_id": "sess_iso"
    }
    resp_alpha = client.post("/api/ai/invoice-processing/process", headers=_auth_headers("tenant_company_alpha"), json=payload)
    assert resp_alpha.status_code == 200
    assert resp_alpha.json()["duplicate_check"]["is_duplicate"] is False

    resp_alpha_dup = client.post("/api/ai/invoice-processing/process", headers=_auth_headers("tenant_company_alpha"), json=payload)
    assert resp_alpha_dup.json()["duplicate_check"]["is_duplicate"] is True

    resp_beta = client.post("/api/ai/invoice-processing/process", headers=_auth_headers("tenant_company_beta"), json=payload)
    assert resp_beta.status_code == 200
    assert resp_beta.json()["duplicate_check"]["is_duplicate"] is False
    assert resp_beta.json()["tenant_id"] == "tenant_company_beta"


def test_saas_multitenant_ledger_isolation():
    """Verify ledgers, CSV export, and unauthenticated demo visitors never leak across partitions."""
    alpha_ids = [inv["id"] for inv in client.get("/api/ai/invoice-processing/ledger?limit=10", headers=_auth_headers("tenant_company_alpha")).json()["invoices"]]
    beta_ids = [inv["id"] for inv in client.get("/api/ai/invoice-processing/ledger?limit=10", headers=_auth_headers("tenant_company_beta")).json()["invoices"]]
    assert len(alpha_ids) >= 1 and len(beta_ids) >= 1
    assert not set(alpha_ids).intersection(set(beta_ids))

    csv_alpha = client.get("/api/ai/invoice-processing/export/csv", headers=_auth_headers("tenant_company_alpha")).text
    for b_id in beta_ids:
        assert b_id not in csv_alpha

    # Secret Corp posted by visitor A cannot be seen by visitor B's session or unauthenticated GET
    client.post(
        "/api/ai/invoice-processing/process",
        headers={"X-Session-ID": "visitor_a_123456"},
        json={"raw_text": "Vendor: Secret Corp\nInvoice No: SEC-999\nTotal: $999.00", "filename": "sec.txt"}
    )
    assert client.get("/api/ai/invoice-processing/ledger").status_code == 401
    visitor_b = client.get("/api/ai/invoice-processing/ledger", headers={"X-Session-ID": "visitor_b_123456"}).json()
    assert all(inv["vendor"] != "Secret Corp" for inv in visitor_b["invoices"])


def test_p04_parser_regressions():
    """Verify Invoice #: S-1001, Invoice No: LT-5521, single-line Zeta, and non-invoice gibberish."""
    r_gib = parse_text_heuristics("hello this is not an invoice at all")
    assert r_gib.vendor_name is None
    assert r_gib.invoice_number is None
    assert r_gib.confidence_score <= 30

    r_lt = parse_text_heuristics("Invoice No: LT-5521\nVendor: Lahore Traders\nDate: 2026-11-20\nTotal: 500.00")
    assert r_lt.invoice_number == "LT-5521"
    assert r_lt.vendor_name == "Lahore Traders"

    r_s = parse_text_heuristics("Vendor: Acme Corp\nInvoice #: S-1001\nTotal: $250.00")
    assert r_s.invoice_number == "S-1001"

    r_zeta = parse_text_heuristics("Zeta Cloud Solutions - Invoice Number: ZETA-551 - Date: 2026-11-18 - Total: $120.00")
    assert r_zeta.vendor_name == "Zeta Cloud Solutions"
    assert r_zeta.invoice_number == "ZETA-551"


def test_qbo_live_mode_never_fakes_posted_live(monkeypatch):
    """Verify QBO_LIVE_MODE=True with fake creds NEVER returns 'posted_live'."""
    monkeypatch.setattr(settings, "QBO_LIVE_MODE", True)
    monkeypatch.setattr(settings, "QBO_CLIENT_ID", "fake-id")
    monkeypatch.setattr(settings, "QBO_CLIENT_SECRET", "fake-secret")
    monkeypatch.setattr(settings, "QBO_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "QBO_REALM_ID", None)

    inv = InvoiceExtractedData(
        vendor_name="Acme", invoice_number="INV-1", invoice_date="2026-11-20",
        currency="USD", line_items=[LineItem(description="Svc", quantity=1, unit_price=100.0, line_total=100.0)],
        subtotal=100.0, tax_amount=0.0, total_amount=100.0, confidence_score=95
    )
    rec = reconcile_invoice_math(inv)
    res = AccountingAdapter().sync_to_accounting("INV-1", inv, rec)
    assert res["sync_status"] != "posted_live"
    assert res["live_mode"] is False

