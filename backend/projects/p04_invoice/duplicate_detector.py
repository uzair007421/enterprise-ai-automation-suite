"""
Invoice Duplicate Detection Engine
Checks cryptographic file hash (SHA-256) and business composite key (vendor + invoice_number).
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
    vendor_name: str,
    invoice_number: str
) -> DuplicateCheckResult:
    """
    Queries database for identical SHA-256 hash or identical vendor + invoice_number combination.
    """
    db = DatabaseSession()
    try:
        # Check identical content hash
        hash_match = db.fetchone(
            "SELECT id, vendor, invoice_number FROM p04_invoices WHERE file_hash = ?",
            (file_sha256,)
        )
        if hash_match:
            return DuplicateCheckResult(
                is_duplicate=True,
                duplicate_match_id=hash_match["id"],
                match_reason=f"Identical file content (SHA-256: {file_sha256[:12]}...) previously processed as [{hash_match['id']}]"
            )

        # Check composite business key: vendor_name (normalized) + invoice_number (normalized)
        normalized_vendor = vendor_name.strip().lower()
        normalized_inv_num = invoice_number.strip().lower()

        composite_match = db.fetchone(
            "SELECT id, vendor, invoice_number FROM p04_invoices WHERE LOWER(vendor) = ? AND LOWER(invoice_number) = ?",
            (normalized_vendor, normalized_inv_num)
        )
        if composite_match:
            return DuplicateCheckResult(
                is_duplicate=True,
                duplicate_match_id=composite_match["id"],
                match_reason=f"Duplicate invoice number '{invoice_number}' for vendor '{vendor_name}' already exists in ledger as [{composite_match['id']}]"
            )

        return DuplicateCheckResult(is_duplicate=False)
    finally:
        db.close()
