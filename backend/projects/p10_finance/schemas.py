"""
Project 10: FinGuard Autonomous Financial Agent Schemas
Contracts for ReAct tool invocation, human cryptographic write gates,
RBAC signing, and tamper-evident SHA-256 audit blocks.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class AgentQueryRequest(BaseModel):
    query: str = Field(description="User prompt or command (e.g. 'What is our treasury balance?' or 'Transfer $5,000 to AWS')")
    user_id: str = Field(default="user_analyst_1", description="Identifier of the querying user")
    role: str = Field(default="ANALYST", description="'ANALYST', 'MANAGER', or 'CFO'")
    session_id: Optional[str] = "demo_session"

class ToolCallProposal(BaseModel):
    proposal_id: str
    tool_name: str
    tool_type: str  # "READ" (autonomous) or "WRITE" (gated)
    parameters: Dict[str, Any]
    reasoning: str
    requires_human_approval: bool
    payload_sha256: str
    status: str  # "EXECUTED_AUTONOMOUSLY" | "PENDING_HUMAN_APPROVAL" | "APPROVED_EXECUTED" | "REJECTED"
    result: Optional[Dict[str, Any]] = None

class AgentQueryResponse(BaseModel):
    session_id: str
    user_id: str
    role: str
    agent_reasoning: str
    tool_proposal: Optional[ToolCallProposal] = None
    direct_answer: Optional[str] = None
    execution_time_ms: float

class ApprovalExecutionRequest(BaseModel):
    proposal_id: str
    approver_id: str = Field(default="cfo_user_99")
    approver_role: str = Field(default="CFO", description="'MANAGER' or 'CFO'")
    secret_key: Optional[str] = Field(default="finguard_secret_hmac_2026", description="HMAC signing secret")
    decision: str = Field(default="APPROVE", description="'APPROVE' or 'REJECT'")
    session_id: Optional[str] = "demo_session"

class ApprovalExecutionResponse(BaseModel):
    proposal_id: str
    status: str  # "APPROVED_EXECUTED" | "REJECTED" | "FORBIDDEN"
    block_index: Optional[int] = None
    block_hash: Optional[str] = None
    hmac_signature: Optional[str] = None
    message: str
    execution_time_ms: float

class AuditBlock(BaseModel):
    id: str
    block_index: int
    previous_hash: str
    action_type: str
    payload_json: str
    actor_role: str
    hmac_signature: str
    block_hash: str
    created_at: str

class AuditChainVerificationResponse(BaseModel):
    is_valid: bool
    total_blocks: int
    genesis_hash: str
    tip_hash: str
    tampered_block_index: Optional[int] = None
    audit_verdict: str
