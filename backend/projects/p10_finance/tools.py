"""
FinGuard ReAct Tools Definition
Separation of Concerns:
- SAFE READ TOOLS: Autonomous execution allowed.
- DANGEROUS WRITE TOOLS: Intercepted and suspended; requires HMAC signing.
"""
from typing import Dict, Any, Optional
import httpx
from core.config import settings
from core.security import validate_url_ssrf_safety

# Mock Enterprise Treasury Accounts
TREASURY_ACCOUNTS = {
    "Operating_Account": 2450000.00,
    "Payroll_Reserve": 850000.00,
    "Tax_Reserve": 420000.00,
    "Capital_Expenditure": 1150000.00
}

VENDOR_INVOICES = {
    "INV-AWS-9021": {"vendor": "Amazon Web Services", "amount": 14250.00, "due_date": "2026-11-28", "status": "PENDING_PAYMENT"},
    "INV-SLK-4412": {"vendor": "Slack Technologies", "amount": 3400.00, "due_date": "2026-12-01", "status": "PENDING_PAYMENT"},
    "INV-GCP-7719": {"vendor": "Google Cloud Platform", "amount": 8920.00, "due_date": "2026-11-30", "status": "PENDING_PAYMENT"}
}

FX_RATES = {
    "USD/EUR": 0.92,
    "USD/GBP": 0.79,
    "USD/PKR": 278.50,
    "USD/CAD": 1.35
}

# --- READ TOOLS (AUTONOMOUS EXECUTION) ---

# Demo SaaS metrics for ARR/MRR/runway queries (replace with live DB in production)
SAAS_METRICS = {
    "arr_usd":        4_800_000.0,   # Annual Recurring Revenue
    "mrr_usd":          400_000.0,   # Monthly Recurring Revenue
    "cash_on_hand_usd": 2_100_000.0, # Cash balance for runway calc
    "monthly_burn_usd":   280_000.0, # Monthly operating burn rate
}

def query_saas_metrics() -> Dict[str, Any]:
    """
    Returns key SaaS financial health indicators: ARR, MRR, and cash runway.
    Runway = cash_on_hand / monthly_burn (months).
    NOTE: Values are illustrative demo figures. Connect to live ERP/data warehouse for production.
    """
    runway_months = round(SAAS_METRICS["cash_on_hand_usd"] / SAAS_METRICS["monthly_burn_usd"], 1)
    return {
        "status": "success",
        "arr_usd": SAAS_METRICS["arr_usd"],
        "mrr_usd": SAAS_METRICS["mrr_usd"],
        "cash_on_hand_usd": SAAS_METRICS["cash_on_hand_usd"],
        "monthly_burn_usd": SAAS_METRICS["monthly_burn_usd"],
        "runway_months": runway_months,
        "data_source": "demo_figures — connect live ERP for production"
    }

def check_treasury_balance() -> Dict[str, Any]:
    """Returns real-time balances across enterprise treasury reserve accounts."""
    total = sum(TREASURY_ACCOUNTS.values())
    return {
        "status": "success",
        "accounts": TREASURY_ACCOUNTS,
        "total_treasury_usd": total
    }

def get_vendor_invoice(invoice_id: str) -> Dict[str, Any]:
    """Retrieves payable invoice information from corporate ERP."""
    normalized = invoice_id.upper().strip()
    if normalized in VENDOR_INVOICES:
        return {"status": "success", "invoice": VENDOR_INVOICES[normalized]}
    return {"status": "not_found", "message": f"Invoice '{invoice_id}' not found in vendor AP registry."}

def query_fx_rates(pair: str) -> Dict[str, Any]:
    """Retrieves foreign exchange conversion spot rates."""
    norm = pair.upper().strip()
    rate = FX_RATES.get(norm, 1.0)
    return {"status": "success", "pair": norm, "rate": rate}

# --- WRITE TOOLS (EXECUTION MUST BE GATED BY HMAC_SECURED HUMAN APPROVAL) ---

def execute_transfer_funds(source: str, destination: str, amount: float, memo: str) -> Dict[str, Any]:
    """
    Mutates local treasury balance in sandbox mode, or dispatches a real bank API call
    when FIN_BANK_LIVE_MODE=True and FIN_BANK_API_URL + FIN_BANK_API_KEY are configured.
    Never claims a live bank wire succeeded when configuration or HTTP fails.
    """
    if settings.FIN_BANK_LIVE_MODE:
        if not (settings.FIN_BANK_API_URL and settings.FIN_BANK_API_KEY):
            return {
                "status": "LIVE_BANK_CONFIG_INCOMPLETE",
                "execution_mode": "blocked",
                "action": "WIRE_TRANSFER",
                "message": "FIN_BANK_LIVE_MODE=True requires FIN_BANK_API_URL and FIN_BANK_API_KEY.",
                "live_executed": False,
            }
        if not validate_url_ssrf_safety(settings.FIN_BANK_API_URL):
            return {
                "status": "LIVE_BANK_URL_REJECTED",
                "execution_mode": "blocked",
                "action": "WIRE_TRANSFER",
                "message": "FIN_BANK_API_URL failed SSRF validation.",
                "live_executed": False,
            }
        try:
            resp = httpx.post(
                settings.FIN_BANK_API_URL,
                json={"source": source, "destination": destination, "amount": amount, "memo": memo},
                headers={"Authorization": f"Bearer {settings.FIN_BANK_API_KEY}"},
                timeout=8.0,
            )
            if 200 <= resp.status_code < 300:
                if source in TREASURY_ACCOUNTS:
                    TREASURY_ACCOUNTS[source] -= amount
                return {
                    "status": "LIVE_BANK_EXECUTED",
                    "execution_mode": "live_bank_api",
                    "action": "WIRE_TRANSFER",
                    "source": source,
                    "destination": destination,
                    "amount": amount,
                    "memo": memo,
                    "http_status": resp.status_code,
                    "remaining_source_balance": TREASURY_ACCOUNTS.get(source, 0.0),
                    "live_executed": True,
                }
            return {
                "status": "LIVE_BANK_HTTP_ERROR",
                "execution_mode": "failed",
                "action": "WIRE_TRANSFER",
                "http_status": resp.status_code,
                "message": f"Bank API returned HTTP {resp.status_code}; transfer was NOT executed.",
                "live_executed": False,
            }
        except Exception as exc:
            return {
                "status": "LIVE_BANK_NETWORK_ERROR",
                "execution_mode": "failed",
                "action": "WIRE_TRANSFER",
                "message": f"Bank API request failed ({type(exc).__name__}); transfer was NOT executed.",
                "live_executed": False,
            }

    if source in TREASURY_ACCOUNTS:
        TREASURY_ACCOUNTS[source] -= amount
    return {
        "status": "MUTATION_EXECUTED",
        "execution_mode": "sandbox_ledger",
        "action": "WIRE_TRANSFER",
        "source": source,
        "destination": destination,
        "amount": amount,
        "memo": memo,
        "remaining_source_balance": TREASURY_ACCOUNTS.get(source, 0.0),
        "live_executed": False,
    }

def execute_ledger_update(account: str, amount: float, direction: str, reference: str) -> Dict[str, Any]:
    """Writes an adjusting journal entry to the general ledger."""
    return {
        "status": "MUTATION_EXECUTED",
        "action": "JOURNAL_ENTRY",
        "account": account,
        "amount": amount,
        "direction": direction,
        "reference": reference
    }

def execute_credit_limit_update(entity: str, amount: float) -> Dict[str, Any]:
    """Updates credit facility limit for specified enterprise account."""
    return {
        "status": "MUTATION_EXECUTED",
        "action": "CREDIT_LIMIT_UPDATE",
        "entity": entity,
        "amount": amount
    }
