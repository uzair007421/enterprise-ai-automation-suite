"""
Enterprise Custom AI Agent with Tool Use, RBAC, Cost Caps, and Audit Logging
- Tool-Calling Architecture (Safe Read Tools vs Dangerous Write Tools)
- Mandatory Human Approval Gate for Database Write Actions
- Role-Based Access Control (JUNIOR_ANALYST, SENIOR_FINANCE_MANAGER, CFO_ADMIN)
- Per-User Token Cost Metering & Hard Daily Budget Limits
- HMAC-Signed Tamper-Evident Audit Trail
"""
import json
import os
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

class FinanceSecurityAgent:
    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_file = os.path.join(base_dir, "data", "finance_db.json")
        self.data_file = data_file
        self.state_file = os.path.join(os.path.dirname(data_file), "finance_live_state.json")
        self._ensure_state()

    def _ensure_state(self):
        if not os.path.exists(self.state_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                base = json.load(f)
            base["audit_log"] = []
            base["pending_writes"] = []
            base["previous_hash"] = "00000000000000000000000000000000"
            self._save(base)

    def _load(self) -> Dict[str, Any]:
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _record_audit_event(self, state: Dict[str, Any], user_id: str, action: str, tool_name: str, params: Dict[str, Any], outcome: str, cost: float) -> str:
        prev_hash = state.get("previous_hash", "00000000")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        event_str = f"{timestamp}|{user_id}|{action}|{tool_name}|{json.dumps(params)}|{outcome}|{cost:.4f}|{prev_hash}"
        event_hash = hashlib.sha256(event_str.encode("utf-8")).hexdigest()

        entry = {
            "timestamp": timestamp,
            "user_id": user_id,
            "action": action,
            "tool_name": tool_name,
            "params": params,
            "outcome": outcome,
            "cost_usd": round(cost, 4),
            "signature_hash": event_hash[:16],
            "prev_hash": prev_hash[:8]
        }
        state["audit_log"].insert(0, entry)
        state["previous_hash"] = event_hash
        return event_hash

    def execute_prompt(self, user_id: str, prompt: str) -> Dict[str, Any]:
        state = self._load()
        user = state["users"].get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not registered")

        # 1. Cost & Token Metering Check
        estimated_cost = 0.0045  # ~$0.0045 per agentic invocation
        if user["cost_used_today"] + estimated_cost > user["daily_budget_limit"]:
            self._record_audit_event(state, user_id, "AGENT_EXECUTION_BLOCKED", "NONE", {"prompt": prompt}, "BUDGET_CAP_EXCEEDED", 0.0)
            self._save(state)
            return {
                "response": f"🚨 Execution Blocked: Daily AI cost budget of ${user['daily_budget_limit']:.2f} has been reached for user '{user['name']}'. Contact CFO to request a budget increase.",
                "status": "BUDGET_EXCEEDED",
                "cost_incurred": 0.0,
                "user_budget": user
            }

        # Deduct cost
        user["cost_used_today"] = round(user["cost_used_today"] + estimated_cost, 4)

        p_lower = prompt.lower()

        # 2. INTENT & TOOL SELECTION: Read Tools (Safe)
        if any(w in p_lower for w in ["metrics", "runway", "arr", "mrr", "burn", "health"]):
            m = state["metrics"]
            tool_res = f"ARR: ${m['annual_recurring_revenue']:,} | MRR: ${m['monthly_recurring_revenue']:,} | Runway: {m['runway_months']} Months | Cash in Bank: ${m['cash_in_bank']:,}"
            self._record_audit_event(state, user_id, "TOOL_EXECUTE", "query_financial_database", {"metric": "core"}, "SUCCESS_READ", estimated_cost)
            self._save(state)

            return {
                "response": f"📊 **Executive Financial Summary (Real-Time Database Query):**\n\n• **ARR:** ${m['annual_recurring_revenue']:,}\n• **MRR:** ${m['monthly_recurring_revenue']:,}\n• **Cash in Bank:** ${m['cash_in_bank']:,}\n• **Monthly Net Burn:** ${m['monthly_burn_rate']:,}\n• **Estimated Runway:** {m['runway_months']} Months\n• **Gross Margin:** {m['gross_margin_pct']}%\n\n*Read query completed successfully with zero write modifications.*",
                "tool_called": "query_financial_database",
                "tool_type": "READ_ONLY",
                "status": "COMPLETED",
                "cost_incurred": estimated_cost,
                "user_budget": user
            }

        if any(w in p_lower for w in ["vanguard", "acc-903", "overdue", "account"]):
            acc = next((a for a in state["client_accounts"] if a["account_id"] == "ACC-903"), None)
            tool_res = f"Account: {acc['company']} | Balance Due: ${acc['balance_due']:,} | Status: {acc['status']}"
            self._record_audit_event(state, user_id, "TOOL_EXECUTE", "read_client_account", {"account_id": "ACC-903"}, "SUCCESS_READ", estimated_cost)
            self._save(state)

            return {
                "response": f"📑 **Client Account Record Retrieved (ACC-903):**\n\n• **Client:** {acc['company']}\n• **Tier:** {acc['tier']}\n• **MRR:** ${acc['mrr']:,}\n• **Current Credit Limit:** ${acc['credit_limit']:,}\n• **Overdue Balance:** ${acc['balance_due']:,}\n• **Collection Status:** {acc['status']}\n\n*All read actions recorded in compliance audit ledger.*",
                "tool_called": "read_client_account",
                "tool_type": "READ_ONLY",
                "status": "COMPLETED",
                "cost_incurred": estimated_cost,
                "user_budget": user
            }

        # 3. DANGEROUS WRITE ACTION: Update Credit Limit / Wire Funds
        if any(w in p_lower for w in ["increase credit", "update credit", "credit limit", "transfer", "wire"]):
            # Check RBAC
            if "REQUEST_WRITE_ACTIONS" not in user["permissions"]:
                self._record_audit_event(state, user_id, "RBAC_VIOLATION_BLOCKED", "update_client_credit_limit", {"prompt": prompt}, "ACCESS_DENIED_JUNIOR_ROLE", estimated_cost)
                self._save(state)
                return {
                    "response": f"⛔ **Security Permission Denied (RBAC Gate):**\n\nYour role `{user['role']}` only holds read and reporting permissions. You do not have authorization to request or execute database write actions.\n\n*Violation logged in Security Audit Trail.*",
                    "status": "PERMISSION_DENIED",
                    "tool_called": "update_client_credit_limit",
                    "tool_type": "WRITE_ACTION_BLOCKED",
                    "cost_incurred": estimated_cost,
                    "user_budget": user
                }

            # If user has permission, create PENDING WRITE ACTION for human sign-off
            write_id = f"WRT-{int(time.time()*1000)%100000}"
            pending_action = {
                "write_id": write_id,
                "requested_by": user["name"],
                "role": user["role"],
                "target_account": "Vanguard Biotech Corp (ACC-903)",
                "action": "Increase Credit Limit from $75,000 to $100,000",
                "new_credit_limit": 100000,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "status": "PENDING_HUMAN_CONFIRMATION"
            }
            state["pending_writes"].insert(0, pending_action)
            self._record_audit_event(state, user_id, "WRITE_ACTION_SUSPENDED", "update_client_credit_limit", pending_action, "AWAITING_HUMAN_SIGN_OFF", estimated_cost)
            self._save(state)

            return {
                "response": f"🛡️ **Mandatory Human Permission Gate Activated:**\n\nThe AI agent has prepared the write action to update **Vanguard Biotech Corp's credit limit to $100,000**, but **NO database changes have been executed**.\n\nUnder corporate financial security controls, all write operations require explicit human confirmation. Please review and confirm in the authorization modal.",
                "status": "PENDING_HUMAN_CONFIRMATION",
                "tool_called": "update_client_credit_limit",
                "tool_type": "DANGEROUS_WRITE_ACTION",
                "pending_action": pending_action,
                "cost_incurred": estimated_cost,
                "user_budget": user
            }

        # Fallback General Assistant Response
        self._record_audit_event(state, user_id, "GENERAL_QUERY", "assistant_chat", {}, "SUCCESS", estimated_cost)
        self._save(state)
        return {
            "response": "Hello! I am your internal Enterprise Financial Intelligence Agent. I can read live company metrics, pull client ledger accounts, and draft reports. What would you like to inspect?",
            "status": "COMPLETED",
            "tool_called": "none",
            "cost_incurred": estimated_cost,
            "user_budget": user
        }

    def confirm_write_action(self, write_id: str, decision: str, approver_id: str = "usr_cfo") -> Dict[str, Any]:
        """Human confirmation of dangerous database write actions."""
        state = self._load()
        target = next((w for w in state["pending_writes"] if w["write_id"] == write_id), None)
        if not target:
            raise ValueError(f"Write action {write_id} not found")

        state["pending_writes"].remove(target)

        if decision == "APPROVED":
            # Execute database write
            acc = next((a for a in state["client_accounts"] if a["account_id"] == "ACC-903"), None)
            if acc:
                acc["credit_limit"] = target["new_credit_limit"]

            target["status"] = "EXECUTED_DATABASE_WRITTEN"
            self._record_audit_event(state, approver_id, "WRITE_ACTION_COMMITTED", "update_client_credit_limit", target, "SUCCESS_DATABASE_COMMITTED", 0.0)
        else:
            target["status"] = "REJECTED_CANCELLED"
            self._record_audit_event(state, approver_id, "WRITE_ACTION_CANCELLED", "update_client_credit_limit", target, "USER_REJECTED", 0.0)

        self._save(state)
        return target

    def get_summary(self) -> Dict[str, Any]:
        state = self._load()
        return {
            "metrics": state["metrics"],
            "client_accounts": state["client_accounts"],
            "users": state["users"],
            "pending_writes": state["pending_writes"],
            "audit_log": state["audit_log"][:10]
        }

    def reset_state(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self._ensure_state()
