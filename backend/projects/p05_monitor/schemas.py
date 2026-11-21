"""
Project 05: Self-Healing Workflow Monitor Schemas
Strict contracts for chaos fault injection, autonomous self-healing,
plain-English LLM diagnostics, and telemetry uptime measurement.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ChaosInjectionRequest(BaseModel):
    workflow_id: str = Field(default="wf_meta_leads_01", description="Target workflow identifier")
    fault_type: str = Field(
        default="HTTP_429_RATE_LIMIT",
        description="'HTTP_429_RATE_LIMIT', 'HTTP_401_TOKEN_EXPIRED', 'HTTP_504_GATEWAY_TIMEOUT', or 'HTTP_500_SERVER_ERROR'"
    )
    simulated_service: str = Field(default="Meta Lead Ads Sync", description="Downstream service name")
    session_id: Optional[str] = "demo_session"

class DiagnosisReport(BaseModel):
    category: str = Field(description="Error category (e.g., API_THROTTLING, AUTH_EXPIRATION, UPSTREAM_OUTAGE)")
    plain_english_summary: str = Field(description="Clear explanation without technical jargon for non-engineers")
    technical_root_cause: str = Field(description="Specific HTTP or protocol trigger")
    recommended_recovery_action: str = Field(description="Autonomous remediation strategy selected")

class HealingExecutionResult(BaseModel):
    workflow_id: str
    workflow_name: str
    fault_type: str
    initial_http_status: int
    recovery_strategy: str
    attempts_required: int
    recovery_time_ms: float
    final_status: str  # "RECOVERED" | "CIRCUIT_OPEN" | "FAILED"
    diagnosis: DiagnosisReport
    telegram_dispatched: bool
    persisted_telemetry_id: str

class WorkflowStatus(BaseModel):
    id: str
    name: str
    category: str
    target_service: str
    health_status: str  # "HEALTHY" | "DEGRADED" | "RECOVERING" | "CRITICAL"
    circuit_state: str  # "CLOSED" | "OPEN" | "HALF_OPEN"
    last_probe_status: int
    last_healed_timestamp: Optional[str] = None

class TelemetrySummary(BaseModel):
    total_monitored_workflows: int
    total_probes_recorded: int
    successful_probes: int
    measured_uptime_percent: float
    avg_recovery_time_ms: float
    active_circuit_breakers: int
    recent_incidents: List[Dict[str, Any]]
