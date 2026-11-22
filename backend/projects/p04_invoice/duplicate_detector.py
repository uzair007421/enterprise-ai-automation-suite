"""
Invoice Duplicate Detection Engine
Checks HMAC-secured file hash (SHA-256) and business composite key (vendor + invoice_number).
Prevents double-entry in the accounting ledger.
"""
import hashlib
from typing import Optional
from core.db import DatabaseSession
from .schemas import DuplicateCheckResult

def calculate_sha256(content: bytes) -> str:
    """Calculates SHA-256 digest of invoice binary or text content."""
    return hashlib.sha256(content).hexdigest()

def check_duplicate_invoice(
    file_sha256: str,
    vendor_name: Optional[str] = None,
    invoice_number: Optional[str] = None,
    amount: Optional[float] = None
) -> DuplicateCheckResult:
    """
    Queries database for identical SHA-256 hash or identical vendor + invoice_number (+ amount) combination,
    including invoices waiting in the review queue.
    """
    db = DatabaseSession()
    try:
        # Check identical content hash
        hash_match = db.fetchone(
            "SELECT id, vendor, invoice_number, status FROM p04_invoices WHERE file_hash = ?",
            (file_sha256,)
        )
        if hash_match:
            status_desc = f" ({hash_match['status']})" if hash_match.get("status") else ""
            return DuplicateCheckResult(
                is_duplicate=True,
                duplicate_match_id=hash_match["id"],
                match_reason=f"Identical file content (SHA-256: {file_sha256[:12]}...) previously processed as [{hash_match['id']}]{status_desc}"
            )

        if vendor_name and invoice_number:
            normalized_vendor = vendor_name.strip().lower()
            normalized_inv_num = invoice_number.strip().lower()

            # Check composite business key: vendor_name + invoice_number (+ optional amount)
            if amount is not None:
                composite_match = db.fetchone(
                    "SELECT id, vendor, invoice_number, status FROM p04_invoices WHERE LOWER(vendor) = ? AND LOWER(invoice_number) = ? AND ABS(amount - ?) < 0.02",
                    (normalized_vendor, normalized_inv_num, amount)
                )
            else:
                composite_match = db.fetchone(
                    "SELECT id, vendor, invoice_number, status FROM p04_invoices WHERE LOWER(vendor) = ? AND LOWER(invoice_number) = ?",
                    (normalized_vendor, normalized_inv_num)
                )

            if composite_match:
                queue_label = "review queue" if composite_match.get("status") in ("REVIEW_REQUIRED", "NEEDS_REVIEW") else "ledger"
                return DuplicateCheckResult(
                    is_duplicate=True,
                    duplicate_match_id=composite_match["id"],
                    match_reason=f"Duplicate invoice number '{invoice_number}' for vendor '{vendor_name}' already exists in {queue_label} as [{composite_match['id']}]"
                )

        return DuplicateCheckResult(is_duplicate=False)
    finally:
        db.close()
