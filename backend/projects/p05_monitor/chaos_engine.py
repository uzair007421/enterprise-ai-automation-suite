"""
Chaos Injection Engine & Production Workflow Registry
Maintains 40 distinct enterprise pipeline registries and manages controllable fault states.
"""
import time
from typing import Dict, Any, List, Optional

ENTERPRISE_SERVICES = [
    ("wf_meta_leads_01", "Meta Lead Ads to CRM Real-Time Sync", "Marketing Automation", "Meta Graph API v19.0"),
    ("wf_hubspot_enrich_02", "HubSpot Contact Enrichment & Scoring", "RevOps & Sales", "HubSpot REST API"),
    ("wf_stripe_billing_03", "Stripe Recurring Billing Webhook Ingestion", "Finance & Treasury", "Stripe Webhooks API"),
    ("wf_google_ads_04", "Google Ads Offline Conversion Dispatcher", "Performance Marketing", "Google Ads API v16"),
    ("wf_shopify_fulfill_05", "Shopify Fulfillment & Courier Dispatch", "E-Commerce Logistics", "Shopify Fulfillment API"),
    ("wf_salesforce_06", "Salesforce Opportunity Stage Sync", "Enterprise CRM", "Salesforce REST API v59"),
    ("wf_zendesk_07", "Zendesk VIP Ticket Router", "Customer Support", "Zendesk Support API v2"),
    ("wf_marketo_08", "Marketo Account-Based Lead Stream", "Marketing Operations", "Marketo REST API"),
    ("wf_snowflake_09", "Snowflake Behavioral Data Warehouse Pipeline", "Data Engineering", "Snowflake SQL API"),
    ("wf_datadog_10", "Datadog APM Alert Aggregator", "Observability", "Datadog API v2"),
    ("wf_aws_sqs_11", "AWS SQS Dead Letter Queue Consumer", "Cloud Infrastructure", "Amazon SQS REST"),
    ("wf_twilio_12", "Twilio Multi-Factor Authentication Relay", "Security & Auth", "Twilio Messaging v1"),
    ("wf_sendgrid_13", "SendGrid Transactional Receipt Relay", "Communications", "SendGrid Mail v3"),
    ("wf_workday_14", "Workday Employee Onboarding Provisioner", "Human Resources", "Workday Human Resources API"),
    ("wf_netsuite_15", "NetSuite Ledger & Invoice Synchronization", "ERP & Accounting", "NetSuite SuiteTalk REST"),
    ("wf_jira_16", "Jira Service Desk Escalation Router", "ITSM & DevOps", "Atlassian Jira Cloud REST"),
    ("wf_github_17", "GitHub Deployment Status Webhook", "CI/CD & Engineering", "GitHub REST API v3"),
    ("wf_pagerduty_18", "PagerDuty High-Urgency Incident Bridge", "On-Call Operations", "PagerDuty REST v2"),
    ("wf_bigquery_19", "Google BigQuery Marketing Attribution", "Data Warehousing", "Google BigQuery v2"),
    ("wf_intercom_20", "Intercom Real-Time Visitor Qualification", "Customer Success", "Intercom API v2.9"),
    ("wf_klaviyo_21", "Klaviyo Cart Abandonment Trigger Fleet", "E-Commerce Marketing", "Klaviyo Track API"),
    ("wf_slack_22", "Slack Executive Metrics Digest Bot", "Internal Tools", "Slack Webhook API"),
    ("wf_qbo_23", "QuickBooks Online Sales Receipt Sync", "Finance Automation", "Intuit QBO REST v3"),
    ("wf_docusign_24", "DocuSign Executed Contract Signoff Hook", "Legal Operations", "DocuSign eSignature v2.1"),
    ("wf_asana_25", "Asana Sprint Task Automation Bridge", "Project Management", "Asana REST API v1.0"),
    ("wf_freshdesk_26", "Freshdesk Omnichannel Support Dispatcher", "Customer Service", "Freshdesk REST v2"),
    ("wf_paypal_27", "PayPal Merchant Dispute Monitor", "Payment Gateways", "PayPal Orders v2"),
    ("wf_mailchimp_28", "Mailchimp Audience Segment Synchronizer", "Email Marketing", "Mailchimp Marketing v3"),
    ("wf_okta_29", "Okta Single Sign-On Identity Provisioner", "Identity & Access", "Okta Core API v1"),
    ("wf_amplitude_30", "Amplitude Product Funnel Event Stream", "Product Analytics", "Amplitude HTTP V2"),
    ("wf_mixpanel_31", "Mixpanel Behavioral Event Collector", "Mobile Analytics", "Mixpanel Ingest v1"),
    ("wf_chargebee_32", "Chargebee Subscription Lifecycle Bridge", "SaaS Billing", "Chargebee REST v2"),
    ("wf_braze_33", "Braze Mobile Push Notification Engine", "User Engagement", "Braze REST v1"),
    ("wf_segment_34", "Segment Customer Data Platform Router", "Data Ingestion", "Segment Tracking API"),
    ("wf_mongo_35", "MongoDB Atlas Change Stream Relayer", "Database Streaming", "MongoDB Data API"),
    ("wf_redis_36", "Redis Cache Invalidation Dispatcher", "Caching Layer", "Redis Sentinel Protocol"),
    ("wf_zoom_37", "Zoom Meeting Recording Archive Stream", "Media Processing", "Zoom API v2"),
    ("wf_linear_38", "Linear Issue Tracking Automation Link", "Engineering Workflow", "Linear GraphQL API"),
    ("wf_notion_39", "Notion Workspace Knowledge Base Sync", "Documentation", "Notion API v1"),
    ("wf_cloudflare_40", "Cloudflare WAF IP Blocklist Ingestion", "Cybersecurity", "Cloudflare REST v4")
]

REGISTERED_WORKFLOWS: Dict[str, Dict[str, Any]] = {}

for wf_id, name, cat, svc in ENTERPRISE_SERVICES:
    REGISTERED_WORKFLOWS[wf_id] = {
        "id": wf_id,
        "name": name,
        "category": cat,
        "target_service": svc,
        "target_url": f"/api/ai/workflow-monitor/chaos-target/{wf_id}",
        "health_status": "HEALTHY",
        "circuit_state": "CLOSED",
        "last_probe_status": 200,
        "consecutive_failures": 0,
        "last_healed_timestamp": None
    }

# Local Chaos Target State Store (in-memory per workflow)
CHAOS_STATES: Dict[str, Dict[str, Any]] = {}

def get_chaos_state(workflow_id: str) -> Dict[str, Any]:
    if workflow_id not in CHAOS_STATES:
        CHAOS_STATES[workflow_id] = {
            "fault_type": None,
            "attempts": 0,
            "token_refreshed": False,
            "circuit_state": "CLOSED"
        }
    return CHAOS_STATES[workflow_id]

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
        elif fault_type in ("HTTP_500_PERMANENT", "HTTP_500_SERVER_ERROR"):
            return 500, '{"error": {"code": 500, "message": "Internal service dependency failure. Permanent hardware outage."}}'
        else:
            return 500, f'{{"error": {{"code": 500, "message": "Unknown fault mode \'{fault_type}\'"}}}}'

chaos_engine = ChaosEngine()
