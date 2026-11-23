"""
FinGuard ReAct Agent Core
Determines whether query requires read tools or write operations.
- Autonomous read tools execute immediately.
- Write operations are intercepted and suspended into PENDING_HUMAN_APPROVAL.
- Investment advice requests are strictly refused without tool calls.
- Unmapped requests receive a polite refusal without tool calls.
"""
import re
import json
import uuid
from typing import Dict, Any, Tuple, Optional
from core.db import DatabaseSession
from .schemas import ToolCallProposal
from .tools import (
    check_treasury_balance,
    get_vendor_invoice,
    query_fx_rates,
    query_saas_metrics
)
from .crypto_gate import hash_payload

def parse_financial_amount(text: str) -> float:
    """Extracts numeric financial amounts including k/m suffixes ($100k, 50k, $1.5m)."""
    m = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*([km])\b", text, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        multiplier = 1000.0 if m.group(2).lower() == 'k' else 1000000.0
        return val * multiplier
    m2 = re.search(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)", text)
    if m2:
        try:
            return float(m2.group(1).replace(",", ""))
        except Exception:
            return 0.0
    return 0.0

class FinGuardAgent:

    def process_query(self, query: str, user_id: str, role: str, tenant_id: str = "tenant_default") -> Tuple[str, Optional[ToolCallProposal], Optional[str]]:
        """
        Returns: (reasoning, tool_proposal, direct_answer)
        """
        q_lower = query.lower()

        # 1. COMPLIANCE GUARDRAIL: Strict Refusal for Investment Advice
        advice_terms = [
            "recommend an investment", "investment portfolio", "buy stock", "invest in",
            "financial advice", "portfolio advice", "recommend portfolio", "stock pick",
            "crypto advice", "wealth management", "asset allocation", "trading strategy"
        ]
        if any(term in q_lower for term in advice_terms):
            reasoning = "Query asks for investment advice or portfolio recommendations. Prohibited by regulatory compliance guardrails."
            answer = "I am a financial operations and treasury automation assistant. In compliance with corporate policy and financial regulations, I cannot provide investment advice, portfolio recommendations, or asset allocation strategies."
            return reasoning, None, answer

        # 2. WRITE: Credit Limit Mutation (e.g. "increase Vanguard credit limit to $100k")
        if re.search(r"\bcredit\s+(?:limit|line)\b", q_lower) or re.search(r"\b(?:increase|update|raise|set)\s+.*?\s+credit\b", q_lower):
            amount = parse_financial_amount(query)
            if amount <= 0.0:
                amount = 100000.0

            # Extract entity name
            entity = "Vanguard"
            m_entity = re.search(r"(?:increase|update|set|raise)\s+([A-Za-z0-9_\-\.\s]+?)\s+(?:credit\s+limit|credit\s+line)", query, re.IGNORECASE)
            if m_entity:
                extracted = m_entity.group(1).strip()
                if extracted:
                    entity = extracted
            elif "vanguard" in q_lower:
                entity = "Vanguard"

            params = {
                "entity": entity,
                "amount": amount,
                "account": entity
            }
            digest = hash_payload(params)
            proposal_id = f"PROP-WRITE-{uuid.uuid4().hex[:6].upper()}"

            reasoning = (
                f"Action involves mutating credit limit facility: setting credit limit for {entity} to ${amount:,.2f}. "
                f"MANDATORY HUMAN APPROVAL WRITE GATE ENGAGED: Autonomous execution is prohibited. "
                f"Generated Action Proposal {proposal_id} suspended in PENDING_HUMAN_APPROVAL state."
            )

            # Persist proposal in SQLite
            db = DatabaseSession()
            try:
                db.execute(
                    """
                    INSERT INTO p10_proposals 
                    (proposal_id, tenant_id, tool_name, tool_type, parameters_json, payload_sha256, reasoning, status, created_by, created_at)
                    VALUES (?, ?, 'update_credit_limit', 'WRITE', ?, ?, ?, 'PENDING_HUMAN_APPROVAL', ?, datetime('now'))
                    """,
                    (proposal_id, tenant_id, json.dumps(params), digest, reasoning, user_id)
                )
                db.commit()
            finally:
                db.close()

            proposal = ToolCallProposal(
                proposal_id=proposal_id,
                tool_name="update_credit_limit",
                tool_type="WRITE",
                parameters=params,
                reasoning=reasoning,
                requires_human_approval=True,
                payload_sha256=digest,
                status="PENDING_HUMAN_APPROVAL",
                result=None,
                tenant_id=tenant_id
            )

            answer = (
                f"⚠️ **Human Approval Write Gate Engaged**\n\n"
                f"Formulated execution proposal to update credit limit for **{entity}** to **${amount:,.2f}**.\n"
                f"• Proposal ID: `{proposal_id}`\n"
                f"• Payload SHA-256 Digest: `{digest[:16]}...`\n"
                f"• Status: `PENDING_HUMAN_APPROVAL`\n\n"
                f"Requires authorized HMAC-SHA256 signature from a **{'CFO' if amount >= 10000 else 'Manager or CFO'}**."
            )
            return reasoning, proposal, answer

        # 3. WRITE: Wire Transfer / Fund Movement / Payment
        is_write_intent = (
            any(w in q_lower for w in ["transfer", "wire", "payout", "send $", "disburse"]) or
            bool(re.search(r"\b(?:pay|send)\s+\$?[0-9]", q_lower)) or
            bool(re.search(r"\bpay\s+(?:invoice|vendor|bill)\b", q_lower))
        )
        if is_write_intent:
            amount = parse_financial_amount(query)
            if amount <= 0.0:
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
                f"MANDATORY HUMAN APPROVAL WRITE GATE ENGAGED: Autonomous agent execution is strictly prohibited. "
                f"Generated Action Proposal {proposal_id} suspended in PENDING_HUMAN_APPROVAL state."
            )

            db = DatabaseSession()
            try:
                db.execute(
                    """
                    INSERT INTO p10_proposals 
                    (proposal_id, tenant_id, tool_name, tool_type, parameters_json, payload_sha256, reasoning, status, created_by, created_at)
                    VALUES (?, ?, 'transfer_funds', 'WRITE', ?, ?, ?, 'PENDING_HUMAN_APPROVAL', ?, datetime('now'))
                    """,
                    (proposal_id, tenant_id, json.dumps(params), digest, reasoning, user_id)
                )
                db.commit()
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
                result=None,
                tenant_id=tenant_id
            )

            answer = (
                f"⚠️ **Human Approval Write Gate Engaged**\n\n"
                f"The AI Agent has formulated an execution proposal to transfer **${amount:,.2f}** to **{dest}**.\n"
                f"• Proposal ID: `{proposal_id}`\n"
                f"• Payload SHA-256 Digest: `{digest[:16]}...`\n"
                f"• Status: `PENDING_HUMAN_APPROVAL`\n\n"
                f"This action requires an authorized HMAC-SHA256 signature from a **{'CFO' if amount >= 10000 else 'Manager or CFO'}** before execution."
            )
            return reasoning, proposal, answer

        # 4. WRITE: Ledger Update / Journal Entry
        if any(w in q_lower for w in ["ledger", "journal entry", "adjust balance", "post entry"]):
            amount = parse_financial_amount(query)
            if amount <= 0.0:
                amount = 2500.00
            account = "General_Ledger_Adjustments"
            params = {
                "account": account,
                "amount": amount,
                "direction": "CREDIT",
                "reference": f"Entry requested by {user_id}"
            }
            digest = hash_payload(params)
            proposal_id = f"PROP-WRITE-{uuid.uuid4().hex[:6].upper()}"

            reasoning = (
                f"Action involves modifying financial ledger: adjusting {account} by ${amount:,.2f}. "
                f"MANDATORY HUMAN APPROVAL WRITE GATE ENGAGED. Proposal {proposal_id} suspended in PENDING_HUMAN_APPROVAL state."
            )

            db = DatabaseSession()
            try:
                db.execute(
                    """
                    INSERT INTO p10_proposals 
                    (proposal_id, tenant_id, tool_name, tool_type, parameters_json, payload_sha256, reasoning, status, created_by, created_at)
                    VALUES (?, ?, 'update_ledger', 'WRITE', ?, ?, ?, 'PENDING_HUMAN_APPROVAL', ?, datetime('now'))
                    """,
                    (proposal_id, tenant_id, json.dumps(params), digest, reasoning, user_id)
                )
                db.commit()
            finally:
                db.close()

            proposal = ToolCallProposal(
                proposal_id=proposal_id,
                tool_name="update_ledger",
                tool_type="WRITE",
                parameters=params,
                reasoning=reasoning,
                requires_human_approval=True,
                payload_sha256=digest,
                status="PENDING_HUMAN_APPROVAL",
                result=None,
                tenant_id=tenant_id
            )
            answer = f"Formulated ledger update proposal {proposal_id} for ${amount:,.2f}. Pending human authorization."
            return reasoning, proposal, answer

        # 5. READ: Check Treasury Balance
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

        # 6. READ: Get Vendor Invoice
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

        # 7. READ: SaaS Metrics — ARR, MRR, Runway
        saas_kw = ["arr", "mrr", "runway", "annual recurring", "monthly recurring", "burn rate", "burn", "cash runway"]
        if any(kw in q_lower for kw in saas_kw):
            res = query_saas_metrics()
            reasoning = "Query requests SaaS financial health metrics (ARR/MRR/runway). Executing autonomous read tool 'query_saas_metrics'."
            answer = (
                f"SaaS Financial Metrics (Demo Figures):\n"
                f"• ARR: ${res['arr_usd']:,.0f}\n"
                f"• MRR: ${res['mrr_usd']:,.0f}\n"
                f"• Cash on Hand: ${res['cash_on_hand_usd']:,.0f}\n"
                f"• Monthly Burn: ${res['monthly_burn_usd']:,.0f}\n"
                f"• Runway: {res['runway_months']} months\n"
                f"⚠️ Note: {res['data_source']}"
            )
            proposal = ToolCallProposal(
                proposal_id=f"PROP-READ-{uuid.uuid4().hex[:6].upper()}",
                tool_name="query_saas_metrics",
                tool_type="READ",
                parameters={},
                reasoning=reasoning,
                requires_human_approval=False,
                payload_sha256=hash_payload({}),
                status="EXECUTED_AUTONOMOUSLY",
                result=res,
                tenant_id=tenant_id
            )
            return reasoning, proposal, answer

        # 8. READ: FX Rates
        if "fx" in q_lower or "exchange rate" in q_lower or "pkr" in q_lower or "eur" in q_lower or "gbp" in q_lower:
            pair = "USD/PKR" if "pkr" in q_lower else ("USD/GBP" if "gbp" in q_lower else "USD/EUR")
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

        # 9. Unmapped Request: Polite Refusal Without Tool Call
        reasoning = "Query cannot be mapped to any authorized financial tool or treasury procedure."
        answer = "I could not map your request to an authorized treasury operation. I can assist with: treasury balances, vendor invoices, FX rates, SaaS metrics (ARR/MRR/runway), and gated write operations (wire transfers, credit limits, ledger adjustments)."
        return reasoning, None, answer

finguard_agent = FinGuardAgent()
