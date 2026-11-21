"""
Invoice-to-Accounting Autonomous Pipeline
- OCR / Vision Data Extraction
- Mathematical Integrity Validation
- Duplicate Invoice Detection
- Suspicious Amount Anomaly Detection
- Low-Confidence Review Queue & Accounting Ledger Push (QuickBooks/Xero format)
"""
import json
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

class InvoicePipeline:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
        self.data_dir = data_dir
        self.db_file = os.path.join(data_dir, "accounting_ledger.json")
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.db_file):
            initial_data = {
                "ledger": [],
                "review_queue": [],
                "rejected": [],
                "signatures": {}
            }
            self._save_db(initial_data)

    def _load_db(self) -> Dict[str, Any]:
        with open(self.db_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_db(self, data: Dict[str, Any]):
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def process_invoice(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        db = self._load_db()
        flags = []
        is_valid = True

        # 1. Math Integrity Check
        calc_subtotal = sum(item["amount"] for item in invoice.get("line_items", []))
        stated_subtotal = float(invoice.get("subtotal", 0.0))
        stated_tax = float(invoice.get("tax", 0.0))
        stated_total = float(invoice.get("total", 0.0))

        if abs(calc_subtotal - stated_subtotal) > 0.05:
            flags.append({
                "type": "MATH_LINE_ITEM_MISMATCH",
                "severity": "HIGH",
                "detail": f"Sum of line items (${calc_subtotal:,.2f}) does not match subtotal (${stated_subtotal:,.2f})"
            })
            is_valid = False

        expected_total = stated_subtotal + stated_tax
        if abs(expected_total - stated_total) > 0.05:
            flags.append({
                "type": "MATH_TOTAL_MISMATCH",
                "severity": "CRITICAL",
                "detail": f"Subtotal (${stated_subtotal:,.2f}) + Tax (${stated_tax:,.2f}) = ${expected_total:,.2f}, but invoice states ${stated_total:,.2f}"
            })
            is_valid = False

        # 2. Duplicate Detection
        signature = f"{invoice['vendor'].lower()}|{invoice['invoice_number'].lower()}|{stated_total:.2f}"
        sig_hash = hashlib.md5(signature.encode("utf-8")).hexdigest()

        if sig_hash in db["signatures"]:
            existing_id = db["signatures"][sig_hash]
            flags.append({
                "type": "DUPLICATE_INVOICE_DETECTED",
                "severity": "CRITICAL",
                "detail": f"Exact invoice already recorded in ledger as [{existing_id}] (Vendor: {invoice['vendor']}, Inv #: {invoice['invoice_number']})"
            })
            is_valid = False

        # 3. Suspicious High Value / Fraud Anomaly Check
        if stated_total >= 10000.00:
            flags.append({
                "type": "HIGH_VALUE_AUDIT_REQUIRED",
                "severity": "MEDIUM",
                "detail": f"Invoice total (${stated_total:,.2f}) exceeds mandatory $10,000 internal audit threshold"
            })
            is_valid = False

        # 4. Confidence Score Calculation
        ocr_confidence = float(invoice.get("raw_ocr_confidence", 0.90))
        confidence = ocr_confidence
        if flags:
            confidence = min(confidence, 0.65)

        record = {
            "invoice_id": invoice.get("id"),
            "vendor": invoice["vendor"],
            "invoice_number": invoice["invoice_number"],
            "date": invoice["date"],
            "due_date": invoice["due_date"],
            "currency": invoice["currency"],
            "subtotal": stated_subtotal,
            "tax": stated_tax,
            "total": stated_total,
            "line_items": invoice.get("line_items", []),
            "ocr_confidence": round(confidence * 100, 1),
            "flags": flags,
            "signature_hash": sig_hash,
            "processed_at": datetime.utcnow().isoformat()
        }

        # 5. Routing: Auto-push or Review Queue
        if is_valid and confidence >= 0.85:
            record["status"] = "SYNCED_TO_ACCOUNTING"
            record["accounting_ref"] = f"QB-{sig_hash[:8].upper()}"
            db["ledger"].insert(0, record)
            db["signatures"][sig_hash] = record["invoice_id"]
        else:
            record["status"] = "PENDING_ACCOUNTANT_REVIEW"
            db["review_queue"].insert(0, record)

        self._save_db(db)
        return record

    def review_action(self, invoice_id: str, decision: str, corrected_total: Optional[float] = None, note: str = "") -> Dict[str, Any]:
        """Human accountant review sign-off."""
        db = self._load_db()
        target = None
        for item in db["review_queue"]:
            if item["invoice_id"] == invoice_id:
                target = item
                break

        if not target:
            raise ValueError(f"Invoice {invoice_id} not found in review queue")

        db["review_queue"].remove(target)

        if decision == "APPROVE":
            if corrected_total is not None:
                target["total"] = corrected_total
            target["status"] = "SYNCED_TO_ACCOUNTING (MANUAL_OVERRIDE)"
            target["accounting_ref"] = f"QB-REV-{target['signature_hash'][:6].upper()}"
            target["accountant_note"] = note
            db["ledger"].insert(0, target)
            db["signatures"][target["signature_hash"]] = target["invoice_id"]
        else:
            target["status"] = "REJECTED_FLAGGED"
            target["accountant_note"] = note
            db["rejected"].insert(0, target)

        self._save_db(db)
        return target

    def get_summary(self) -> Dict[str, Any]:
        db = self._load_db()
        return {
            "ledger_count": len(db["ledger"]),
            "review_queue_count": len(db["review_queue"]),
            "rejected_count": len(db["rejected"]),
            "recent_ledger": db["ledger"][:10],
            "review_queue": db["review_queue"]
        }

    def reset_db(self):
        initial_data = {
            "ledger": [],
            "review_queue": [],
            "rejected": [],
            "signatures": {}
        }
        self._save_db(initial_data)
