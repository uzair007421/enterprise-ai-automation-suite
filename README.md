Working prototypes. Rule-based engines by default; optional LLM mode with your own API key.

# Enterprise AI Multi-Agent & Automation Engineering Portfolio
**Architect:** Muhammad Uzair  
**Portfolio Hub:** [https://uzairio.web.app/ai-automations](https://uzairio.web.app/ai-automations)  
**Backend:** FastAPI 0.115+, Pydantic v2, SQLite WAL Mode  
**Test Suite:** 52 / 52 Passed (100% Green)

A portfolio of 10 working enterprise AI automation prototypes. Every system executes live backend logic with rule-based fallbacks, enforces human-in-the-loop security gates, and logs to real database audit trails.

---

## Complete Truthfulness & Implementation Audit Table

| # | Project Slug | Feature | Implementation Status | Source File & Line |
|---|---|---|---|---|
| **01** | `p01_real_estate` | 100-Point Buyer Qualification Rubric | **Real** | [agent_qualifier.py](backend/projects/p01_real_estate/agent_qualifier.py#L15-L120) |
| **01** | `p01_real_estate` | MLS Inventory Database Matcher | **Real** | [agent_matcher.py](backend/projects/p01_real_estate/agent_matcher.py#L62-L120) |
| **01** | `p01_real_estate` | Policy-Bound Offer Drafter (2% earnest lock) | **Real** | [agent_drafter.py](backend/projects/p01_real_estate/agent_drafter.py#L17-L50) |
| **01** | `p01_real_estate` | Human Broker Approval Gate | **Real** | [router.py](backend/projects/p01_real_estate/router.py#L115-L165) |
| **01** | `p01_real_estate` | HubSpot Deals & Contacts Sync | **Live / Sandbox Fallback** | [crm_adapter.py](backend/projects/p01_real_estate/crm_adapter.py#L17-L55) |
| **02** | `p02_legal` | 128-D Dense Vector Embeddings Engine | **Real** | [vector_engine.py](backend/projects/p02_legal/vector_engine.py#L12-L45) |
| **02** | `p02_legal` | Mathematical Cosine Similarity Search | **Real** | [vector_engine.py](backend/projects/p02_legal/vector_engine.py#L46-L80) |
| **02** | `p02_legal` | Character Substring Quote Citation Verifier | **Real** | [citation_verifier.py](backend/projects/p02_legal/citation_verifier.py#L10-L40) |
| **02** | `p02_legal` | Ungrounded Semantic Refusal Gate | **Real** | [citation_verifier.py](backend/projects/p02_legal/citation_verifier.py#L35-L65) |
| **03** | `p03_support` | Roman Urdu & English Intent/Sentiment Classifier | **Real** | [classifier.py](backend/projects/p03_support/classifier.py#L18-L60) |
| **03** | `p03_support` | Code-Level Strict Refund Blocking Barrier | **Real** | [guardrails.py](backend/projects/p03_support/guardrails.py#L15-L45) |
| **03** | `p03_support` | Shopify Orders Sync & SQLite Sandbox | **Live / Sandbox Fallback** | [shopify_adapter.py](backend/projects/p03_support/shopify_adapter.py#L18-L60) |
| **03** | `p03_support` | Supervisor Telegram Escalation Alerter | **Live / Sandbox Fallback** | [telegram_adapter.py](backend/projects/p03_support/telegram_adapter.py#L15-L45) |
| **04** | `p04_invoice` | Tesseract Neural & Vision Field Extractor | **Real** | [ocr_engine.py](backend/projects/p04_invoice/ocr_engine.py#L15-L55) |
| **04** | `p04_invoice` | 4-Way Mathematical Reconciliation Engine | **Real** | [reconciliation.py](backend/projects/p04_invoice/reconciliation.py#L12-L65) |
| **04** | `p04_invoice` | SHA-256 & Vendor Composite Duplicate Detector | **Real** | [duplicate_detector.py](backend/projects/p04_invoice/duplicate_detector.py#L12-L50) |
| **04** | `p04_invoice` | QuickBooks Online & CSV Ledger Exporter | **Live / Sandbox Fallback** | [accounting_adapter.py](backend/projects/p04_invoice/accounting_adapter.py#L15-L60) |
| **05** | `p05_monitor` | 40-Workflow Observability & Chaos Fault Simulator | **Real** | [chaos_engine.py](backend/projects/p05_monitor/chaos_engine.py#L15-L65) |
| **05** | `p05_monitor` | Jittered Exponential Backoff & Circuit Breaker | **Real** | [self_healing.py](backend/projects/p05_monitor/self_healing.py#L18-L85) |
| **05** | `p05_monitor` | Production n8n Sentinel Workflow Definition | **Real** | [self_healing_sentinel.json](backend/infra/n8n/self_healing_sentinel.json) |
| **05** | `p05_monitor` | Plain-English Diagnostic Explainer | **Real** | [self_healing.py](backend/projects/p05_monitor/self_healing.py#L55-L95) |
| **06** | `p06_hr` | Demographic PII Anonymizer (Blind Screening) | **Real** | [pii_redactor.py](backend/projects/p06_hr/pii_redactor.py#L12-L65) |
| **06** | `p06_hr` | Objective 100-Point Competency Rubric | **Real** | [rubric_evaluator.py](backend/projects/p06_hr/rubric_evaluator.py#L25-L95) |
| **06** | `p06_hr` | Calendar Interview Slot Proposer | **Real** | [rubric_evaluator.py](backend/projects/p06_hr/rubric_evaluator.py#L75-L90) |
| **07** | `p07_voice` | 98%+ Emergency Dental Recall Triage Engine | **Real** | [triage_engine.py](backend/projects/p07_voice/triage_engine.py#L25-L85) |
| **07** | `p07_voice` | Doctor Anti-Conflict Booking Engine | **Real** | [router.py](backend/projects/p07_voice/router.py#L40-L90) |
| **07** | `p07_voice` | Twilio SMS Confirmation Adapter | **Live / Sandbox Fallback** | [notification_adapter.py](backend/projects/p07_voice/notification_adapter.py#L15-L45) |
| **08** | `p08_competitor` | Anti-SSRF Crawler Security Filter | **Real** | [crawler.py](backend/projects/p08_competitor/crawler.py#L12-L40) |
| **08** | `p08_competitor` | DOM Semantic Diffing Engine | **Real** | [diff_engine.py](backend/projects/p08_competitor/diff_engine.py#L20-L85) |
| **08** | `p08_competitor` | 1-10 Strategic Impact Severity Scorer | **Real** | [diff_engine.py](backend/projects/p08_competitor/diff_engine.py#L40-L95) |
| **09** | `p09_media` | 1-to-4 Multi-Format Repurposing Engine | **Real** | [repurposing_engine.py](backend/projects/p09_media/repurposing_engine.py#L25-L125) |
| **09** | `p09_media` | Brand Voice Anti-Hype Guardrail | **Real** | [repurposing_engine.py](backend/projects/p09_media/repurposing_engine.py#L15-L35) |
| **09** | `p09_media` | Social Publishing Adapters (LinkedIn/X/Dev.to) | **Live / Sandbox Fallback** | [social_adapters.py](backend/projects/p09_media/social_adapters.py#L15-L55) |
| **10** | `p10_finance` | Autonomous ReAct Read Tools | **Real** | [tools.py](backend/projects/p10_finance/tools.py#L15-L65) |
| **10** | `p10_finance` | Write Action Interception & Suspension Gate | **Real** | [agent.py](backend/projects/p10_finance/agent.py#L35-L95) |
| **10** | `p10_finance` | Cryptographic HMAC-SHA256 Multi-Tier RBAC | **Real** | [crypto_gate.py](backend/projects/p10_finance/crypto_gate.py#L15-L65) |
| **10** | `p10_finance` | Merkle Hash-Linked Tamper-Evident Audit Chain | **Real** | [audit_chain.py](backend/projects/p10_finance/audit_chain.py#L18-L95) |

---

## Running the Complete System Locally

### 1. Launch the Unified FastAPI Backend
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Run the Full Test Suite (52 Tests)
```bash
cd backend
python -m pytest tests/ -v
```

### 3. Run Benchmark Evaluations Across All Projects
```bash
python backend/evals/p04_invoice/runner.py
python backend/evals/p03_support/runner.py
python backend/evals/p05_monitor/runner.py
python backend/evals/p10_finance/runner.py
python backend/evals/p02_legal/runner.py
python backend/evals/p01_real_estate/runner.py
python backend/evals/p07_voice/runner.py
python backend/evals/p06_hr/runner.py
python backend/evals/p09_media/runner.py
python backend/evals/p08_competitor/runner.py
```
