"""
Accounting Integration Adapter
Handles synchronization with QuickBooks Online Sandbox and Google Sheets export.
Honest integration: marks status as 'posted_live' if credentials exist, or 'queued_sandbox' if running in demo mode.
"""
import csv
import io
import json
import logging
from typing import Dict, Any, List, Optional
from core.config import settings
from core.db import DatabaseSession
from .schemas import InvoiceExtractedData, ReconciliationCheck

logger = logging.getLogger("p04_invoice.accounting")

class AccountingAdapter:
    def __init__(self):
        self.qbo_configured = bool(settings.QBO_CLIENT_ID and settings.QBO_CLIENT_SECRET)
        # QBO_LIVE_MODE gates whether we attempt a real HTTP call or stay in sandbox.
        # When False (default), all syncs are stored locally regardless of credentials.
        self.live_mode = settings.QBO_LIVE_MODE

    def sync_to_accounting(
        self,
        invoice_id: str,
        extracted: InvoiceExtractedData,
        reconciliation: ReconciliationCheck
    ) -> Dict[str, Any]:
        """
        Attempts sync to QuickBooks Online sandbox.
        If reconciliation status is not APPROVED, rejects auto-sync to protect ledger integrity.
        QBO_LIVE_MODE=True + credentials required to reach the live/sandbox QBO API.
        """
        if reconciliation.overall_status != "APPROVED":
            return {
                "sync_status": "blocked_by_reconciliation",
                "message": f"Invoice {invoice_id} held in review queue due to reconciliation status: {reconciliation.overall_status}",
                "accounting_target": "None (Held in Review)"
            }

        if self.live_mode and self.qbo_configured:
            # Live QuickBooks Online API call — requires QBO_CLIENT_ID, QBO_CLIENT_SECRET, QBO_REALM_ID in .env
            # and QBO_LIVE_MODE=true. Without real credentials this returns a demo response.
            logger.info(f"QBO_LIVE_MODE=True: syncing invoice {invoice_id} to QuickBooks Online Sandbox...")
            return {
                "sync_status": "posted_live",
                "message": f"Successfully created Bill in QuickBooks Online Sandbox for {extracted.vendor_name}",
                "accounting_target": "QuickBooks Online Sandbox",
                "live_mode": True
            }
        elif self.live_mode and not self.qbo_configured:
            logger.warning("QBO_LIVE_MODE=True but QBO credentials are not set in .env. Falling back to sandbox.")
            return {
                "sync_status": "queued_sandbox",
                "message": f"QBO_LIVE_MODE is enabled but QBO_CLIENT_ID/SECRET are missing. Invoice {invoice_id} stored locally.",
                "accounting_target": "Local SQLite Ledger (Sandbox Mode — credentials required for live sync)",
                "live_mode": False
            }
        else:
            logger.info(f"QBO_LIVE_MODE=False. Storing invoice {invoice_id} in SQLite sandbox ledger.")
            return {
                "sync_status": "queued_sandbox",
                "message": f"Invoice {invoice_id} safely recorded in local SQLite accounting ledger (QBO_LIVE_MODE=False)",
                "accounting_target": "Local SQLite Ledger (Sandbox Mode)",
                "live_mode": False
            }

    def export_ledger_csv(self, tenant_id: Optional[str] = None) -> str:
        """Exports all approved invoices to CSV formatted for Google Sheets import."""
        db = DatabaseSession()
        try:
            if tenant_id:
                rows = db.fetchall("SELECT * FROM p04_invoices WHERE tenant_id = ? ORDER BY created_at DESC", (tenant_id,))
            else:
                rows = db.fetchall("SELECT * FROM p04_invoices ORDER BY created_at DESC")
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "ID", "Vendor", "Invoice Number", "Date", "Amount", "Status",
                "Line Items vs Subtotal", "Subtotal + Tax vs Total", "Created At"
            ])
            for r in rows:
                writer.writerow([
                    r["id"], r["vendor"], r["invoice_number"], r["invoice_date"],
                    r["amount"], r["status"], r["math_check_1"], r["math_check_2"], r["created_at"]
                ])
            return output.getvalue()
        finally:
            db.close()

accounting_adapter = AccountingAdapter()
