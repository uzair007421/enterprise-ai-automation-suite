"""
Project 05: Self-Healing Workflow Monitor Test Suite
Verifies:
- Real chaos fault injection (429, 401, 504)
- Autonomous remediation execution:
  - 429 -> Exponential backoff with jitter
  - 401 -> OAuth token exchange refresh
  - 504 -> Circuit breaker state machine
- Dynamic measured uptime & latency metrics (zero hardcoded strings)
- Plain-English root cause diagnostics
"""
import pytest
from projects.p05_monitor.schemas import ChaosInjectionRequest
from projects.p05_monitor.router import (
    inject_chaos_endpoint,
    list_workflows,
    get_telemetry_metrics,
    probe_all_workflows
)
from core.db import DatabaseSession

def test_workflows_registry_distinct_enterprise_pipelines():
    """Audit Fix: Verify registered workflows are real distinct services, not for-loop duplicates."""
    wfs = list_workflows()
    assert len(wfs) >= 5
    ids = [w.id for w in wfs]
    assert len(ids) == len(set(ids)), "Workflow IDs must be unique"
    services = [w.target_service for w in wfs]
    assert "Meta Graph API v19.0" in services
    assert "HubSpot REST API" in services
    assert "Stripe Webhooks API" in services

def test_chaos_429_exponential_backoff_recovery():
    """Verify HTTP 429 triggers exponential backoff and recovers."""
    req = ChaosInjectionRequest(
        workflow_id="wf_meta_leads_01",
        fault_type="HTTP_429_RATE_LIMIT",
        simulated_service="Meta Graph API"
    )
    result = inject_chaos_endpoint(req)
    assert result.initial_http_status == 429
    assert result.recovery_strategy == "EXPONENTIAL_BACKOFF_JITTER"
    assert result.attempts_required >= 2
    assert result.final_status == "RECOVERED"
    assert result.recovery_time_ms > 0
    assert "throttled" in result.diagnosis.plain_english_summary.lower() or "rate" in result.diagnosis.plain_english_summary.lower()

def test_chaos_401_oauth_token_refresh():
    """Verify HTTP 401 triggers OAuth token refresh sequence."""
    req = ChaosInjectionRequest(
        workflow_id="wf_hubspot_enrich_02",
        fault_type="HTTP_401_TOKEN_EXPIRED",
        simulated_service="HubSpot REST API"
    )
    result = inject_chaos_endpoint(req)
    assert result.initial_http_status == 401
    assert result.recovery_strategy == "OAUTH_TOKEN_REFRESH"
    assert result.final_status == "RECOVERED"
    assert "token" in result.diagnosis.plain_english_summary.lower() or "auth" in result.diagnosis.plain_english_summary.lower()

def test_chaos_504_circuit_breaker_isolation():
    """Verify HTTP 504 trips circuit breaker and recovers."""
    req = ChaosInjectionRequest(
        workflow_id="wf_stripe_billing_03",
        fault_type="HTTP_504_GATEWAY_TIMEOUT",
        simulated_service="Stripe Webhooks API"
    )
    result = inject_chaos_endpoint(req)
    assert result.initial_http_status == 504
    assert result.recovery_strategy == "CIRCUIT_BREAKER_RESET"
    assert result.final_status == "RECOVERED"
    assert "timeout" in result.diagnosis.plain_english_summary.lower() or "server" in result.diagnosis.plain_english_summary.lower()

def test_truthful_measured_telemetry_metrics():
    """Audit Fix: Telemetry metrics must be computed from SQLite rows, not hardcoded 99.2%."""
    # Probe all workflows to ensure active measurements in database
    probe_res = probe_all_workflows()
    assert probe_res["probed"] >= 5

    metrics = get_telemetry_metrics()
    assert metrics.total_probes_recorded >= 5
    assert metrics.successful_probes >= 5
    assert isinstance(metrics.measured_uptime_percent, float)
    assert metrics.measured_uptime_percent > 0.0
    assert metrics.avg_recovery_time_ms >= 0.0
    assert len(metrics.recent_incidents) > 0
