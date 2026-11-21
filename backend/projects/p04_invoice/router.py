"""
Invoice Processing & 4-Way Reconciliation Router
Routes mounted under /api/ai/invoice-processing
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Response
from pydantic import BaseModel
from core.db import DatabaseSession
from core.events import event_broker
from core.health import record_project_activity
from .schemas import (
    InvoiceExtractedData,
    InvoiceProcessResponse,
    InvoiceProcessRequest,
    LineItem,
    ReconciliationCheck,
    DuplicateCheckResult
)
from .ocr_engine import extract_invoice_from_content
from .reconciliation import reconcile_invoice_math
from .duplicate_detector import calculate_sha256, check_duplicate_invoice
from .accounting_adapter import accounting_adapter

router = APIRouter(prefix="/api/ai/invoice-processing", tags=["Invoice Processing Pipeline"])

@router.post("/process", response_model=InvoiceProcessResponse)
def process_invoice_endpoint(request: InvoiceProcessRequest):
    """
    Main invoice ingestion endpoint.
    Performs OCR extraction, 4-way math check, duplicate detection, and ledger sync.
    """
    start_time = time.time()
    record_project_activity("invoice-processing")
    session_id = request.session_id or "demo_session"

    # Step 1: Ingest & Compute Cryptographic Content Hash
    event_broker.publish(session_id, {
        "step": "FILE_INGESTION",
        "detail": f"Received document payload '{request.filename}'",
        "timestamp": time.time()
    })

    if request.manual_data:
        extracted = request.manual_data
        raw_bytes = str(extracted.model_dump()).encode("utf-8")
    elif request.raw_text:
        raw_bytes = request.raw_text.encode("utf-8")
        event_broker.publish(session_id, {
            "step": "OCR_EXTRACTION",
            "detail": "Calling multimodal structured extraction engine...",
            "timestamp": time.time()
        })
        extracted = extract_invoice_from_content(request.raw_text, request.filename or "document.txt")
    else:
        raise HTTPException(status_code=400, detail="Either 'raw_text' or 'manual_data' must be supplied.")

    file_hash = calculate_sha256(raw_bytes)
    invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"

    # Step 2: 4-Way Math Reconciliation
    event_broker.publish(session_id, {
        "step": "MATH_RECONCILIATION",
        "detail": f"Verifying {len(extracted.line_items)} line items against stated subtotal (${extracted.subtotal}) and total (${extracted.total_amount})",
        "timestamp": time.time()
    })
    reconciliation = reconcile_invoice_math(extracted)

    # Step 3: Duplicate Detection Check
    event_broker.publish(session_id, {
        "step": "DUPLICATE_CHECK",
        "detail": f"Querying ledger for SHA-256 hash {file_hash[:12]}... and composite key ({extracted.vendor_name}, {extracted.invoice_number})",
        "timestamp": time.time()
    })
    duplicate_res = check_duplicate_invoice(
        file_sha256=file_hash,
        vendor_name=extracted.vendor_name,
        invoice_number=extracted.invoice_number
    )

    # Determine status & Save to SQLite
    if duplicate_res.is_duplicate:
        status_code = "DUPLICATE_REJECTED"
        sync_result = {
            "sync_status": "rejected",
            "message": f"Rejected: {duplicate_res.match_reason}"
        }
    elif reconciliation.overall_status != "APPROVED":
        status_code = "REVIEW_REQUIRED"
        sync_result = accounting_adapter.sync_to_accounting(invoice_id, extracted, reconciliation)
    else:
        status_code = "APPROVED"
        sync_result = accounting_adapter.sync_to_accounting(invoice_id, extracted, reconciliation)

    # Persist in SQLite
    db = DatabaseSession()
    try:
        db.execute(
            """
            INSERT INTO p04_invoices 
            (id, vendor, invoice_number, invoice_date, amount, status, math_check_1, math_check_2, file_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                extracted.vendor_name,
                extracted.invoice_number,
                extracted.invoice_date,
                extracted.total_amount,
                status_code,
                "PASS" if reconciliation.line_items_vs_subtotal_matched else "FAIL",
                "PASS" if reconciliation.subtotal_plus_tax_vs_total_matched else "FAIL",
                file_hash,
                datetime.now(timezone.utc).isoformat()
            )
        )
    finally:
        db.close()

    elapsed = round((time.time() - start_time) * 1000, 2)
    event_broker.publish(session_id, {
        "step": "EXECUTION_COMPLETE",
        "detail": f"Invoice {invoice_id} processed in {elapsed}ms. Status: {status_code}",
        "timestamp": time.time()
    })

    return InvoiceProcessResponse(
        invoice_id=invoice_id,
        file_sha256=file_hash,
        vendor_name=extracted.vendor_name,
        invoice_number=extracted.invoice_number,
        invoice_date=extracted.invoice_date,
        total_amount=extracted.total_amount,
        currency=extracted.currency,
        confidence_score=extracted.confidence_score,
        extracted=extracted,
        reconciliation=reconciliation,
        duplicate_check=duplicate_res,
        accounting_sync_status=sync_result.get("sync_status", "queued_sandbox"),
        message=sync_result.get("message", "Processed successfully"),
        execution_time_ms=elapsed
    )

@router.post("/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form("demo_session")
):
    """Multipart file upload endpoint accepting PDF, PNG, JPG, or TXT."""
    record_project_activity("invoice-processing")
    contents = await file.read()
    raw_text = contents.decode("utf-8", errors="ignore")
    req = InvoiceProcessRequest(
        raw_text=raw_text if len(raw_text.strip()) > 10 else f"Binary file upload: {file.filename} ({len(contents)} bytes)",
        filename=file.filename,
        session_id=session_id
    )
    return process_invoice_endpoint(req)

@router.get("/ledger")
def get_ledger(limit: int = 50, status_filter: Optional[str] = None):
    """Returns persistent invoices from SQLite database."""
    db = DatabaseSession()
    try:
        if status_filter:
            rows = db.fetchall(
                "SELECT * FROM p04_invoices WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status_filter, limit)
            )
        else:
            rows = db.fetchall(
                "SELECT * FROM p04_invoices ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        return {"total": len(rows), "invoices": rows}
    finally:
        db.close()

@router.get("/export/csv")
def export_csv_endpoint():
    """Generates and downloads CSV ledger for Google Sheets integration."""
    csv_data = accounting_adapter.export_ledger_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=accounting_ledger.csv"}
    )
