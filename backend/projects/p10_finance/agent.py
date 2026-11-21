"""
FinGuard ReAct Agent Core
Determines whether query requires read tools or write operations.
Autonomous read tools execute immediately.
Write operations are intercepted and suspended into PENDING_HUMAN_APPROVAL.
"""
import re
import json
import uuid
from typing import Dict, Any, Tuple, Optional
from core.db import DatabaseSession
from .schemas import ToolCallProposal, AgentQueryResponse
from .tools import (
    check_treasury_balance,
    get_vendor_invoice,
    query_fx_rates
)
from .crypto_gate import hash_payload

class FinGuardAgent:

    def process_query(self, query: str, user_id: str, role: str) -> Tuple[str, Optional[ToolCallProposal], Optional[str]]:
        """
        Returns: (reasoning, tool_proposal, direct_answer)
        """
        q_lower = query.lower()

        # 1. WRITE: Wire Transfer / Fund Movement / Payment (PRIORITY GATE)
        is_write_intent = (
            any(w in q_lower for w in ["transfer", "wire", "payout", "send $", "disburse"]) or
            bool(re.search(r"\b(?:pay|send)\s+\$?[0-9]", q_lower)) or
            bool(re.search(r"\bpay\s+(?:invoice|vendor|bill)\b", q_lower))
        )
        if is_write_intent:
            # Extract amount
            amount_match = re.search(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|\b[0-9]+\b)", q_lower)
            amount = 5000.00
            if amount_match:
                try:
                    amount = float(amount_match.group(1).replace(",", ""))
                except Exception:
                    amount = 5000.00

            dest = "Amazon Web Services (Corporate Wire)" if "aws" in q_lower else "External Vendor Account"
            source = "Operating_Account"
            memo = f"Disbursement authorized by {user_id}"

            params = {
                "source": source,
                "destination": dest,
                "amount": amount,
                "memo": memo
            }
            digest = hash_payload(params)
            proposal_id = f"PROP-WRITE-{uuid.uuid4().hex[:6].upper()}"

            reasoning = (
                f"Action involves mutating financial assets: transferring ${amount:,.2f} from {source} to {dest}. "
                f"MANDATORY CRYPTOGRAPHIC WRITE GATE ENGAGED: Autonomous agent execution is strictly prohibited. "
                f"Generated Action Proposal {proposal_id} suspended in PENDING_HUMAN_APPROVAL state."
            )

            # Persist proposal in SQLite
            db = DatabaseSession()
            try:
                db.execute(
                    """
                    INSERT INTO p10_proposals 
                    (proposal_id, tool_name, tool_type, parameters_json, payload_sha256, reasoning, status, created_by, created_at)
                    VALUES (?, 'transfer_funds', 'WRITE', ?, ?, ?, 'PENDING_HUMAN_APPROVAL', ?, datetime('now'))
                    """,
                    (proposal_id, json.dumps(params), digest, reasoning, user_id)
                )
            finally:
                db.close()

            proposal = ToolCallProposal(
                proposal_id=proposal_id,
                tool_name="transfer_funds",
                tool_type="WRITE",
                parameters=params,
                reasoning=reasoning,
                requires_human_approval=True,
                payload_sha256=digest,
                status="PENDING_HUMAN_APPROVAL",
                result=None
            )

            answer = (
                f"⚠️ **Cryptographic Write Gate Engaged**\n\n"
                f"The AI Agent has formulated an execution proposal to transfer **${amount:,.2f}** to **{dest}**.\n"
                f"• Proposal ID: `{proposal_id}`\n"
                f"• Payload SHA-256 Digest: `{digest[:16]}...`\n"
                f"• Status: `PENDING_HUMAN_APPROVAL`\n\n"
                f"This action requires an authorized HMAC-SHA256 signature from a **{'CFO' if amount >= 10000 else 'Manager or CFO'}** before execution."
            )
            return reasoning, proposal, answer

        # 2. READ: Check Treasury Balance
        if any(w in q_lower for w in ["balance", "treasury", "how much money", "funds available", "how much cash", "payroll reserve"]):
            res = check_treasury_balance()
            reasoning = "Query asks for current account balances. Invoking autonomous read tool 'check_treasury_balance'."
            answer = (
                f"Enterprise Treasury Balances (Total: ${res['total_treasury_usd']:,.2f}):\n"
                f"• Operating Account: ${res['accounts']['Operating_Account']:,.2f}\n"
                f"• Payroll Reserve: ${res['accounts']['Payroll_Reserve']:,.2f}\n"
                f"• Tax Reserve: ${res['accounts']['Tax_Reserve']:,.2f}\n"
                f"• Capital Expenditure: ${res['accounts']['Capital_Expenditure']:,.2f}"
            )
            proposal = ToolCallProposal(
                proposal_id=f"PROP-READ-{uuid.uuid4().hex[:6].upper()}",
                tool_name="check_treasury_balance",
                tool_type="READ",
                parameters={},
                reasoning=reasoning,
                requires_human_approval=False,
                payload_sha256=hash_payload({}),
                status="EXECUTED_AUTONOMOUSLY",
                result=res
            )
            return reasoning, proposal, answer

        # 2. READ: Get Vendor Invoice
        if "invoice" in q_lower:
            m = re.search(r"(?:inv-[a-z0-9\-]+|aws|slack|gcp)", q_lower)
            inv_id = "INV-AWS-9021"
            if m:
                val = m.group(0).upper()
                if "AWS" in val: inv_id = "INV-AWS-9021"
                elif "SLACK" in val: inv_id = "INV-SLK-4412"
                elif "GCP" in val: inv_id = "INV-GCP-7719"

            res = get_vendor_invoice(inv_id)
            reasoning = f"Query inquires about vendor payable invoice. Executing read tool 'get_vendor_invoice' for {inv_id}."
            if res.get("status") == "success":
                inv = res["invoice"]
                answer = f"Invoice {inv_id} from {inv['vendor']}: Amount ${inv['amount']:,.2f}, Due Date: {inv['due_date']}, Status: {inv['status']}."
            else:
                answer = res.get("message", "Invoice not found.")

            proposal = ToolCallProposal(
                proposal_id=f"PROP-READ-{uuid.uuid4().hex[:6].upper()}",
                tool_name="get_vendor_invoice",
                tool_type="READ",
                parameters={"invoice_id": inv_id},
                reasoning=reasoning,
                requires_human_approval=False,
                payload_sha256=hash_payload({"invoice_id": inv_id}),
                status="EXECUTED_AUTONOMOUSLY",
                result=res
            )
            return reasoning, proposal, answer

        # 3. READ: FX Rates
        if "fx" in q_lower or "exchange rate" in q_lower or "pkr" in q_lower or "eur" in q_lower:
            pair = "USD/PKR" if "pkr" in q_lower else "USD/EUR"
            res = query_fx_rates(pair)
            reasoning = f"Query requests currency spot conversion rate. Executing autonomous read tool 'query_fx_rates' for {pair}."
            answer = f"Live FX Spot Rate for {res['pair']}: {res['rate']}."
            proposal = ToolCallProposal(
                proposal_id=f"PROP-READ-{uuid.uuid4().hex[:6].upper()}",
                tool_name="query_fx_rates",
                tool_type="READ",
                parameters={"pair": pair},
                reasoning=reasoning,
                requires_human_approval=False,
                payload_sha256=hash_payload({"pair": pair}),
                status="EXECUTED_AUTONOMOUSLY",
                result=res
            )
            return reasoning, proposal, answer

        # Default conversational query
        reasoning = "General conversational query; no tools required."
        answer = "I am FinGuard, your autonomous financial treasury assistant. You can ask me to check treasury balances, view vendor invoices, query FX rates, or formulate wire transfer proposals."
        return reasoning, None, answer

finguard_agent = FinGuardAgent()
