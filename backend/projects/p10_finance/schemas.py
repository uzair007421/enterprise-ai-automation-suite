"""
Project 10: FinGuard Autonomous Financial Agent Schemas
Contracts for ReAct tool invocation, human cryptographic write gates,
RBAC signing, and tamper-evident SHA-256 audit blocks.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str

class AgentQueryRequest(BaseModel):
    query: str = Field(description="User prompt or command (e.g. 'What is our treasury balance?' or 'Transfer $5,000 to AWS')")
    user_id: Optional[str] = Field(default="analyst", description="Identifier of the querying user (overridden by JWT)")
    role: Optional[str] = Field(default="ANALYST", description="'ANALYST', 'MANAGER', or 'CFO' (overridden by JWT)")
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
    approver_id: Optional[str] = Field(default=None, description="Approver ID (derived strictly from JWT)")
    approver_role: Optional[str] = Field(default=None, description="Approver role (derived strictly from JWT)")
    secret_key: Optional[str] = Field(default=None, description="Deprecated client key; server-held key is used")
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
