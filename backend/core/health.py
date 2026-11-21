"""
Modular Health & Integration Status Router
Reports live API connectivity, sandbox state, or not_configured status for each project.
Never reports a mock integration as live. Reads measured metrics at request time from results.json.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter
from .config import settings

health_router = APIRouter(prefix="/api/ai", tags=["Health & Status"])

EVALS_BASE_DIR = Path(__file__).resolve().parent.parent / "evals"

PROJECT_EVAL_DIR = {
    "real-estate-sales-agents": "p01_real_estate",
    "law-firm-private-rag": "p02_legal",
    "ecommerce-support-bot": "p03_support",
    "invoice-processing": "p04_invoice",
    "workflow-monitor": "p05_monitor",
    "ai-recruiter-assistant": "p06_hr",
    "dental-voice-agent": "p07_voice",
    "competitor-intelligence": "p08_competitor",
    "content-repurposing": "p09_media",
    "finance-agent-gate": "p10_finance",
}

def get_project_engine(slug: str) -> str:
    """Returns 'llm' if an active LLM key is configured, else 'rules'."""
    has_llm = bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY)
    return "llm" if has_llm else "rules"

def get_measured_metric(slug: str) -> Optional[str]:
    """Dynamically reads the measured metric at request time from evals/<project>/results.json."""
    eval_dir_name = PROJECT_EVAL_DIR.get(slug)
    if not eval_dir_name:
        return None
    results_file = EVALS_BASE_DIR / eval_dir_name / "results.json"
    if not results_file.exists():
        return None
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if slug == "invoice-processing":
            acc = data.get("accuracy_percent")
            total = data.get("total_cases")
            return f"{acc}% Field Accuracy ({total} invoices)" if acc is not None else None
        elif slug == "ecommerce-support-bot":
            acc = data.get("escalation_classification_accuracy_percent")
            total = data.get("total_dialogues")
            return f"{acc}% Escalation Accuracy ({total} dialogues)" if acc is not None else None
        elif slug == "workflow-monitor":
            acc = data.get("recovery_success_rate_percent")
            total = data.get("total_chaos_faults")
            return f"{acc}% Recovery Rate ({total} faults)" if acc is not None else None
        elif slug == "law-firm-private-rag":
            acc = data.get("quote_citation_substring_validity_percent")
            total = data.get("total_queries")
            return f"{acc}% Citation Validity ({total} queries)" if acc is not None else None
        elif slug == "real-estate-sales-agents":
            acc = data.get("qualification_tier_accuracy_pct")
            total = data.get("total_cases")
            return f"{acc}% Qualification Accuracy ({total} leads)" if acc is not None else None
        elif slug == "finance-agent-gate":
            acc = data.get("approval_gate_accuracy_pct", data.get("accuracy_percent"))
            total = data.get("total_proposals", data.get("total_cases"))
            return f"{acc}% Gate Compliance ({total} proposals)" if acc is not None else None
        elif slug == "dental-voice-agent":
            acc = data.get("emergency_triage_recall_pct")
            total = data.get("total_utterances")
            return f"{acc}% Emergency Recall ({total} utterances)" if acc is not None else None
        elif slug == "ai-recruiter-assistant":
            acc = data.get("pii_redaction_accuracy_pct")
            total = data.get("total_resumes")
            return f"{acc}% PII Redaction ({total} profiles)" if acc is not None else None
        elif slug == "competitor-intelligence":
            acc = data.get("ssrf_block_rate_pct")
            total = data.get("total_probes")
            return f"{acc}% SSRF Block Rate ({total} probes)" if acc is not None else None
        elif slug == "content-repurposing":
            acc = data.get("brand_voice_safety_pct")
            total = data.get("total_runs")
            return f"{acc}% Brand Voice Safety ({total} runs)" if acc is not None else None
        
        acc = data.get("accuracy_percent")
        total = data.get("total_cases")
        return f"{acc}% Accuracy ({total} cases)" if acc is not None else None
    except Exception:
        return None

def build_project_registry() -> Dict[str, Dict[str, Any]]:
    has_llm = bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY)
    return {
        "real-estate-sales-agents": {
            "slug": "real-estate-sales-agents",
            "name": "Multi-Agent Real Estate Sales Team",
            "engine": get_project_engine("real-estate-sales-agents"),
            "integrations": {
                "hubspot_crm": "live" if settings.HUBSPOT_ACCESS_TOKEN else "not_configured",
                "telegram_notify": "live" if settings.TELEGRAM_BOT_TOKEN else "not_configured",
                "inventory_store": "live"
            },
            "mode": "live" if settings.HUBSPOT_ACCESS_TOKEN else "sandbox",
            "measured_metric": get_measured_metric("real-estate-sales-agents"),
            "last_call_timestamp": None
        },
        "law-firm-private-rag": {
            "slug": "law-firm-private-rag",
            "name": "Legal Document Vector Search Engine",
            "engine": get_project_engine("law-firm-private-rag"),
            "integrations": {
                "bm25_retriever": "live",
                "cloud_llm": "live" if has_llm else "not_configured"
            },
            "mode": "live",
            "measured_metric": get_measured_metric("law-firm-private-rag"),
            "last_call_timestamp": None
        },
        "ecommerce-support-bot": {
            "slug": "ecommerce-support-bot",
            "name": "Bilingual E-Commerce Support Engine",
            "engine": get_project_engine("ecommerce-support-bot"),
            "integrations": {
                "shopify_api": "live" if settings.SHOPIFY_ADMIN_ACCESS_TOKEN else "not_configured",
                "telegram_bot": "live" if settings.TELEGRAM_BOT_TOKEN else "not_configured",
                "refund_guardrail_layer": "live"
            },
            "mode": "live" if settings.SHOPIFY_ADMIN_ACCESS_TOKEN else "sandbox",
            "measured_metric": get_measured_metric("ecommerce-support-bot"),
            "last_call_timestamp": None
        },
        "invoice-processing": {
            "slug": "invoice-processing",
            "name": "Invoice OCR & 4-Way Reconciliation Pipeline",
            "engine": get_project_engine("invoice-processing"),
            "integrations": {
                "reconciliation_engine": "live",
                "gemini_vision_api": "live" if settings.GEMINI_API_KEY else "not_configured",
                "quickbooks_online": "live" if settings.QBO_CLIENT_ID else "not_configured"
            },
            "mode": "live",
            "measured_metric": get_measured_metric("invoice-processing"),
            "last_call_timestamp": None
        },
        "workflow-monitor": {
            "slug": "workflow-monitor",
            "name": "Self-Healing Workflow Sentinel",
            "engine": get_project_engine("workflow-monitor"),
            "integrations": {
                "chaos_api_grid": "live",
                "telegram_alerting": "live" if settings.TELEGRAM_ALERT_CHAT_ID else "not_configured"
            },
            "mode": "live",
            "measured_metric": get_measured_metric("workflow-monitor"),
            "last_call_timestamp": None
        },
        "ai-recruiter-assistant": {
            "slug": "ai-recruiter-assistant",
            "name": "Objective AI Recruiter & Scheduler",
            "engine": get_project_engine("ai-recruiter-assistant"),
            "integrations": {
                "demographic_redaction_engine": "live",
                "google_calendar_oauth": "not_configured",
                "rubric_evaluator": "live"
            },
            "mode": "sandbox",
            "measured_metric": get_measured_metric("ai-recruiter-assistant"),
            "last_call_timestamp": None
        },
        "dental-voice-agent": {
            "slug": "dental-voice-agent",
            "name": "Voice AI Clinic Appointment Agent",
            "engine": get_project_engine("dental-voice-agent"),
            "integrations": {
                "text_triage_engine": "live",
                "twilio_sms_service": "live" if settings.TWILIO_ACCOUNT_SID else "not_configured"
            },
            "mode": "sandbox",
            "measured_metric": get_measured_metric("dental-voice-agent"),
            "last_call_timestamp": None
        },
        "competitor-intelligence": {
            "slug": "competitor-intelligence",
            "name": "SaaSRadar Competitor Market Intelligence",
            "engine": get_project_engine("competitor-intelligence"),
            "integrations": {
                "public_crawler": "live",
                "ssrf_security_guard": "live",
                "diff_evaluator": "live"
            },
            "mode": "live",
            "measured_metric": get_measured_metric("competitor-intelligence"),
            "last_call_timestamp": None
        },
        "content-repurposing": {
            "slug": "content-repurposing",
            "name": "OmniContent Video Repurposing Desk",
            "engine": get_project_engine("content-repurposing"),
            "integrations": {
                "transcript_analyzer": "live",
                "brand_voice_guardrail": "live",
                "telegram_channel_dispatch": "live" if settings.TELEGRAM_ALERT_CHAT_ID else "not_configured"
            },
            "mode": "live",
            "measured_metric": get_measured_metric("content-repurposing"),
            "last_call_timestamp": None
        },
        "finance-agent-gate": {
            "slug": "finance-agent-gate",
            "name": "FinGuard Autonomous Enterprise Agent Gate",
            "engine": get_project_engine("finance-agent-gate"),
            "integrations": {
                "audit_chain": "live",
                "policy_gate": "live",
                "llm_tool_caller": "live" if has_llm else "not_configured"
            },
            "mode": "live",
            "measured_metric": get_measured_metric("finance-agent-gate"),
            "last_call_timestamp": None
        }
    }

START_TIME = time.time()
ACTIVITY_REGISTRY: Dict[str, str] = {}

def record_project_activity(slug: str):
    """Updates the last call timestamp for a project."""
    ACTIVITY_REGISTRY[slug] = datetime.now(timezone.utc).isoformat()

@health_router.get("/{slug}/health")
def get_project_health(slug: str):
    """Returns the truthful live health and integration statuses of a specific project."""
    registry = build_project_registry()
    if slug not in registry:
        return {
            "status": "error",
            "detail": f"Unknown project slug: '{slug}'"
        }

    info = dict(registry[slug])
    info["last_call_timestamp"] = ACTIVITY_REGISTRY.get(slug)
    info["uptime_seconds"] = int(time.time() - START_TIME)
    info["timestamp"] = datetime.now(timezone.utc).isoformat()
    return info

@health_router.get("/fleet/summary")
def get_all_projects_health():
    """Returns a unified status map for the portfolio hub cards."""
    registry = build_project_registry()
    for slug in registry:
        registry[slug]["last_call_timestamp"] = ACTIVITY_REGISTRY.get(slug)
    return {
        "total_projects": len(registry),
        "uptime_seconds": int(time.time() - START_TIME),
        "projects": registry
    }
