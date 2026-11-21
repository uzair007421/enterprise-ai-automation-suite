"""
FinGuard ReAct Tools Definition
Separation of Concerns:
- SAFE READ TOOLS: Autonomous execution allowed.
- DANGEROUS WRITE TOOLS: Intercepted and suspended; requires cryptographic signing.
"""
from typing import Dict, Any, Optional

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

# --- WRITE TOOLS (EXECUTION MUST BE GATED BY CRYPTOGRAPHIC HUMAN APPROVAL) ---

def execute_transfer_funds(source: str, destination: str, amount: float, memo: str) -> Dict[str, Any]:
    """Mutates ledger and executes bank wire transfer."""
    if source in TREASURY_ACCOUNTS:
        TREASURY_ACCOUNTS[source] -= amount
    return {
        "status": "MUTATION_EXECUTED",
        "action": "WIRE_TRANSFER",
        "source": source,
        "destination": destination,
        "amount": amount,
        "memo": memo,
        "remaining_source_balance": TREASURY_ACCOUNTS.get(source, 0.0)
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
