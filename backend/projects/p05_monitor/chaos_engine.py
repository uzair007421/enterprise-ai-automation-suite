"""
Chaos Injection Engine & Production Workflow Registry
Simulates upstream enterprise failure modes:
- 429 Too Many Requests (Rate limit burst)
- 401 Unauthorized (Expired OAuth refresh token)
- 504 Gateway Timeout (Downstream SaaS latency spike)
- 500 Internal Server Error (Database lock contention)
"""
import time
from typing import Dict, Any, List, Optional

REGISTERED_WORKFLOWS: Dict[str, Dict[str, Any]] = {
    "wf_meta_leads_01": {
        "id": "wf_meta_leads_01",
        "name": "Meta Lead Ads to CRM Real-Time Sync",
        "category": "Marketing Automation",
        "target_service": "Meta Graph API v19.0",
        "health_status": "HEALTHY",
        "circuit_state": "CLOSED",
        "last_probe_status": 200,
        "consecutive_failures": 0,
        "last_healed_timestamp": None
    },
    "wf_hubspot_enrich_02": {
        "id": "wf_hubspot_enrich_02",
        "name": "HubSpot Contact Enrichment & Scoring",
        "category": "RevOps & Sales",
        "target_service": "HubSpot REST API",
        "health_status": "HEALTHY",
        "circuit_state": "CLOSED",
        "last_probe_status": 200,
        "consecutive_failures": 0,
        "last_healed_timestamp": None
    },
    "wf_stripe_billing_03": {
        "id": "wf_stripe_billing_03",
        "name": "Stripe Recurring Billing Webhook Ingestion",
        "category": "Finance & Treasury",
        "target_service": "Stripe Webhooks API",
        "health_status": "HEALTHY",
        "circuit_state": "CLOSED",
        "last_probe_status": 200,
        "consecutive_failures": 0,
        "last_healed_timestamp": None
    },
    "wf_google_ads_04": {
        "id": "wf_google_ads_04",
        "name": "Google Ads Offline Conversion Dispatcher",
        "category": "Performance Marketing",
        "target_service": "Google Ads API v16",
        "health_status": "HEALTHY",
        "circuit_state": "CLOSED",
        "last_probe_status": 200,
        "consecutive_failures": 0,
        "last_healed_timestamp": None
    },
    "wf_shopify_fulfill_05": {
        "id": "wf_shopify_fulfill_05",
        "name": "Shopify Fulfillment & Courier Dispatch",
        "category": "E-Commerce Logistics",
        "target_service": "Shopify Fulfillment API",
        "health_status": "HEALTHY",
        "circuit_state": "CLOSED",
        "last_probe_status": 200,
        "consecutive_failures": 0,
        "last_healed_timestamp": None
    }
}

class ChaosEngine:
    """Manages synthetic fault injection and upstream behavior simulation."""

    def simulate_fault(self, fault_type: str) -> tuple[int, str]:
        """Returns (http_status, raw_error_payload)."""
        if fault_type == "HTTP_429_RATE_LIMIT":
            return 429, '{"error": {"code": 429, "message": "Rate limit exceeded. Quota tier exhausted for current minute window."}}'
        elif fault_type == "HTTP_401_TOKEN_EXPIRED":
            return 401, '{"error": {"code": 401, "message": "The access token provided has expired or was revoked by authorization server."}}'
        elif fault_type == "HTTP_504_GATEWAY_TIMEOUT":
            return 504, '{"error": {"code": 504, "message": "Upstream gateway connection timed out after 30000ms."}}'
        else:
            return 500, '{"error": {"code": 500, "message": "Internal service dependency failure."}}'

chaos_engine = ChaosEngine()
