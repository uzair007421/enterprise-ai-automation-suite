# 💼 Project 10: Enterprise Custom AI Agent with Tool Use, RBAC & Audit Logs

> **Commercial Brief:**  
> *"Build an internal agent that can read our database, generate reports and draft emails, but must ask permission before any write action. Keep a full log of every action, enforce role-based access and cost limits per user."*

---

## 🌟 Key Capabilities
* **ReAct Tool-Calling Security Architecture:**
  - **Safe Read Tools (Auto-executed):** `query_financial_database`, `read_client_account`, `draft_invoice_email`.
  - **Dangerous Write Tools (Strictly Gated):** `update_client_credit_limit`, `execute_wire_transfer`.
* **Mandatory Human Confirmation Gate:** No write tool modifies the live database without explicit human modal approval.
* **Granular Role-Based Access Control (RBAC):**
  - `JUNIOR_ANALYST`: Restricted to safe reads and reporting. Write tool attempts are hard-blocked at the gateway.
  - `SENIOR_FINANCE_MANAGER`: Authorized to execute reads and request writes subject to confirmation.
  - `CFO_ADMIN`: Full administrative sign-off authority and budget overrides.
* **Per-User Token & Cost Metering:** Real-time token tracking ($0.002/1k tokens) with hard daily budget caps ($5, $20, $100) to eliminate bill shock.
* **Cryptographic Tamper-Evident Audit Trail:** SHA-256 hash-chained immutable logging of every prompt, tool execution, role, cost, and human sign-off.

---

## 🏗️ Architecture & Security Gate Flow

```
                      [ User Prompt & Query ]
                                 │
                                 ▼
                 [ Cost & Token Metering Check ]
                 (Enforce daily budget caps per user)
                                 │
                                 ▼
                     [ RBAC Permission Gate ]
          Does user role possess required tool permissions?
                                 │
                ┌────────────────┴────────────────┐
                ▼                                 ▼
       [ Permission Denied ]             [ Permission Granted ]
       • Block execution                 • Select Target Tool
       • Log RBAC violation              • Inspect Tool Type
                │                                 │
                │                 ┌───────────────┴───────────────┐
                │                 ▼                               ▼
                │        [ Safe Read Tool ]           [ Dangerous Write Tool ]
                │        (Read DB / Metrics)          (Update Limit / Transfer)
                │                 │                               │
                │                 ▼                               ▼
                │        [ Auto-Execute ]          [ MANDATORY HUMAN CONFIRMATION ]
                │        • Return data             • Suspend execution
                │        • Log to audit            • Await explicit sign-off modal
                │                 │                               │
                │                 │               ┌───────────────┴───────────────┐
                │                 │               ▼                               ▼
                │                 │         [ User Confirmed ]              [ User Denied ]
                │                 │         • Commit to database            • Cancel action
                │                 │         • Log SHA-256 hash              • Log rejection
                ▼                 ▼               ▼                               ▼
          [ ─────────────────────────────── SHA-256 AUDIT LOG ─────────────────────────────── ]
```

---

## ⚡ How to Run Live Interactive Demo

Zero external pip dependencies required. Runs completely using Python standard library:

```bash
cd 10-finance-agent-tool-use-audit
python run_demo.py
```
Open your browser at: **`http://localhost:8010`**

---

## 🎥 60-Second Fiverr Video Recording Script
1. **(0:00 - 0:15) The Hook:**  
   *"Companies want internal AI agents to query databases and draft reports, but they are terrified of rogue LLMs executing unauthorized database writes or running up insane API bills. Here is our Enterprise FinGuard Agent."*
2. **(0:15 - 0:30) Safe Read Tools & Token Cost Meter:**  
   Click: *"What is our current ARR, MRR, cash in bank and runway?"*  
   Show the agent call `query_financial_database` and display real metrics: *"Safe read queries execute in real time while tracking exact per-user token costs against their daily budget cap."*
3. **(0:30 - 0:45) The Mandatory Write Gate & RBAC Block:**  
   Click the **Junior Analyst RBAC test**: Show the immediate red permission denied alert.  
   Then switch to **Senior Manager** and request to increase credit limit: Show the **Human Permission Modal**: *"Notice the AI cannot write to the database alone. It suspends execution until the authorized manager clicks Confirm."*
4. **(0:45 - 1:00) Cryptographic Audit Trail:**  
   Show the live SHA-256 audit ledger: *"Every action is cryptographically hash-chained for internal compliance. Contact me to build secure AI agents for your business!"*

---

## 💼 Fiverr Proposal Pitch Template

```text
Hi [Client Name],

I specialize in building secure, enterprise-grade AI agents with strict tool-calling safeguards, RBAC permissions, and human approval gates.

I have already engineered a production-ready Internal Financial Agent system featuring:
1. ReAct Tool Architecture: Clear separation between auto-executed read tools and gated write tools.
2. Mandatory Write Confirmation Gate: The agent cannot modify databases or dispatch funds without explicit human sign-off.
3. Role-Based Access Control (RBAC): Hierarchical user roles (Analyst vs Manager vs Executive) with strict permission enforcement.
4. Per-User Cost & Token Metering: Hard daily budget ceilings to prevent unexpected OpenAI/Anthropic API bills.
5. Cryptographic Audit Trail: SHA-256 hash-chained immutable activity ledger for SOC2 & corporate compliance.

I can implement this custom agent infrastructure for your company within 4 to 6 business days. Let's start a quick chat for a live demo!
```

---

## 💰 Recommended Fiverr Gig Pricing
* **Basic ($350 - $600):** Custom tool-calling agent with read-only database query tools.
* **Standard ($800 - $1,400):** Tool-calling agent + Mandatory human confirmation gate + RBAC user permissions.
* **Premium ($1,800 - $3,500):** Full Enterprise Internal Agent + Cryptographic audit logging + Token cost metering + Custom ERP/Postgres DB connector.
