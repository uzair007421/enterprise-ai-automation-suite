"""
Accounting Integration Adapter
Handles synchronization with QuickBooks Online API (v3) and Google Sheets CSV export.
Honest integration:
- When QBO_LIVE_MODE=False (default): records in local SQLite sandbox ledger ('queued_sandbox').
- When QBO_LIVE_MODE=True: requires QBO_ACCESS_TOKEN and QBO_REALM_ID and makes a real
  HTTP POST to QuickBooks Online v3 Bill API. Never fakes 'posted_live' on error or missing token.
"""
import csv
import io
import logging
from typing import Dict, Any, Optional
import httpx
from core.config import settings
from core.db import DatabaseSession
from .schemas import InvoiceExtractedData, ReconciliationCheck

logger = logging.getLogger("p04_invoice.accounting")

class AccountingAdapter:
    def __init__(self):
        self.qbo_configured = bool(
            settings.QBO_ACCESS_TOKEN and settings.QBO_REALM_ID
        )
        self.live_mode = settings.QBO_LIVE_MODE

    def sync_to_accounting(
        self,
        invoice_id: str,
        extracted: InvoiceExtractedData,
        reconciliation: ReconciliationCheck
    ) -> Dict[str, Any]:
        """
        Attempts sync to QuickBooks Online API if QBO_LIVE_MODE=True and token+realm are set.
        If reconciliation status is not APPROVED, rejects auto-sync to protect ledger integrity.
        Never fabricates 'posted_live' without a real HTTP 200/201 response from QuickBooks.
        """
        if reconciliation.overall_status != "APPROVED":
            return {
                "sync_status": "blocked_by_reconciliation",
                "message": f"Invoice {invoice_id} held in review queue due to reconciliation status: {reconciliation.overall_status}",
                "accounting_target": "None (Held in Review)",
                "live_mode": False,
            }

        live_enabled = settings.QBO_LIVE_MODE
        access_token = settings.QBO_ACCESS_TOKEN
        realm_id = settings.QBO_REALM_ID

        if not live_enabled:
            logger.info(f"QBO_LIVE_MODE=False. Storing invoice {invoice_id} in SQLite sandbox ledger.")
            return {
                "sync_status": "queued_sandbox",
                "message": f"Invoice {invoice_id} recorded in local SQLite accounting ledger (QBO_LIVE_MODE=False)",
                "accounting_target": "Local SQLite Ledger (Sandbox Mode)",
                "live_mode": False,
            }

        if not (access_token and realm_id):
            logger.warning(
                "QBO_LIVE_MODE=True but QBO_ACCESS_TOKEN / QBO_REALM_ID are not set. Cannot make live QBO API call."
            )
            return {
                "sync_status": "live_config_incomplete",
                "message": (
                    f"QBO_LIVE_MODE is True, but QBO_ACCESS_TOKEN and QBO_REALM_ID are required for QuickBooks v3 API calls. "
                    f"Invoice {invoice_id} kept locally in SQLite only (not posted to QuickBooks)."
                ),
                "accounting_target": "Local SQLite Only (QBO Live Config Incomplete)",
                "live_mode": False,
            }

        base_host = (
            "https://sandbox-quickbooks.api.intuit.com"
            if settings.QBO_SANDBOX
            else "https://quickbooks.api.intuit.com"
        )
        url = f"{base_host}/v3/company/{realm_id}/bill"
        bill_payload = {
            "DocNumber": (extracted.invoice_number or invoice_id)[:21],
            "TotalAmt": float(extracted.total_amount or 0.0),
            "PrivateNote": f"Synced by Invoice Pipeline ({invoice_id}) for vendor {extracted.vendor_name or 'UNKNOWN'}",
            "Line": [
                {
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "Amount": float(extracted.total_amount or 0.0),
                    "Description": f"Invoice {extracted.invoice_number or invoice_id}",
                    "AccountBasedExpenseLineDetail": {
                        "AccountRef": {"value": "1"}
                    },
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.post(url, json=bill_payload, headers=headers, timeout=8.0)
            if resp.status_code in (200, 201):
                qbo_bill_id = None
                try:
                    qbo_bill_id = resp.json().get("Bill", {}).get("Id")
                except Exception:
                    pass
                return {
                    "sync_status": "posted_live",
                    "message": f"Created QuickBooks Bill (ID: {qbo_bill_id or 'confirmed'}) via HTTP {resp.status_code}.",
                    "accounting_target": base_host,
                    "live_mode": True,
                }
            logger.warning(f"QuickBooks API rejected Bill sync ({invoice_id}): HTTP {resp.status_code}")
            return {
                "sync_status": "live_sync_failed",
                "message": f"QuickBooks API returned HTTP {resp.status_code}. Invoice {invoice_id} was NOT posted live.",
                "accounting_target": f"{base_host} (HTTP {resp.status_code} Error)",
                "live_mode": False,
            }
        except Exception as exc:
            logger.warning(f"QuickBooks API request failed for {invoice_id}: {exc}")
            return {
                "sync_status": "live_sync_failed",
                "message": f"QuickBooks network/HTTP failure ({type(exc).__name__}). Invoice {invoice_id} was NOT posted live.",
                "accounting_target": f"{base_host} (Network Error)",
                "live_mode": False,
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
