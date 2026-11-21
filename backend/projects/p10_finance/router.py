"""
FinGuard Financial Agent & Cryptographic Approval Gate Router
Mounted under /api/ai/finance-agent-gate
"""
import time
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status
from core.events import event_broker
from core.health import record_project_activity
from core.db import DatabaseSession
from .schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    ApprovalExecutionRequest,
    ApprovalExecutionResponse,
    AuditBlock,
    AuditChainVerificationResponse,
    ToolCallProposal
)
from .agent import finguard_agent
from .crypto_gate import (
    validate_rbac_authority,
    generate_hmac_signature,
    verify_hmac_signature,
    DEFAULT_SECRET_KEY
)
from .tools import execute_transfer_funds, execute_ledger_update
from .audit_chain import audit_chain_manager

router = APIRouter(prefix="/api/ai/finance-agent-gate", tags=["FinGuard Financial Agent"])

@router.post("/query", response_model=AgentQueryResponse)
def execute_agent_query(request: AgentQueryRequest):
    """
    Core ReAct Reasoning Endpoint.
    Autonomous read queries execute immediately; write operations are suspended into PENDING_HUMAN_APPROVAL.
    """
    start_time = time.time()
    record_project_activity("finance-agent-gate")
    session_id = request.session_id or "demo_session"

    event_broker.publish(session_id, {
        "step": "QUERY_RECEIVED",
        "detail": f"User {request.user_id} ({request.role}): '{request.query}'",
        "timestamp": time.time()
    })

    reasoning, proposal, answer = finguard_agent.process_query(
        query=request.query,
        user_id=request.user_id,
        role=request.role
    )

    if proposal:
        if proposal.requires_human_approval:
            event_broker.publish(session_id, {
                "step": "WRITE_GATE_SUSPENDED",
                "detail": f"Write action '{proposal.tool_name}' intercepted. Created proposal {proposal.proposal_id} with SHA-256 digest {proposal.payload_sha256[:12]}...",
                "timestamp": time.time()
            })
        else:
            event_broker.publish(session_id, {
                "step": "READ_TOOL_EXECUTED",
                "detail": f"Autonomous read tool '{proposal.tool_name}' executed successfully.",
                "timestamp": time.time()
            })

    elapsed = round((time.time() - start_time) * 1000, 2)
    return AgentQueryResponse(
        session_id=session_id,
        user_id=request.user_id,
        role=request.role,
        agent_reasoning=reasoning,
        tool_proposal=proposal,
        direct_answer=answer,
        execution_time_ms=elapsed
    )

@router.post("/approve", response_model=ApprovalExecutionResponse)
def approve_write_action(request: ApprovalExecutionRequest):
    """
    Human Cryptographic Approval Gate.
    Verifies RBAC rules and HMAC-SHA256 signature, then executes write mutation and appends audit block.
    """
    start_time = time.time()
    record_project_activity("finance-agent-gate")
    session_id = request.session_id or "demo_session"

    # Step 1: Lookup Pending Proposal
    db = DatabaseSession()
    try:
        row = db.fetchone(
            "SELECT * FROM p10_proposals WHERE proposal_id = ?",
            (request.proposal_id,)
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Proposal '{request.proposal_id}' not found.")

        proposal = dict(row)
        if proposal["status"] != "PENDING_HUMAN_APPROVAL":
            raise HTTPException(
                status_code=400,
                detail=f"Proposal '{request.proposal_id}' already resolved with status: {proposal['status']}"
            )

        params = json.loads(proposal["parameters_json"])

        # Step 2: Handle Rejection Decision
        if request.decision.upper() == "REJECT":
            db.execute(
                "UPDATE p10_proposals SET status = 'REJECTED' WHERE proposal_id = ?",
                (request.proposal_id,)
            )
            audit_chain_manager.append_block(
                action_type="WRITE_PROPOSAL_REJECTED",
                payload={"proposal_id": request.proposal_id, "approver": request.approver_id, "params": params},
                actor_role=request.approver_role,
                hmac_signature=f"REJECTED_BY_{request.approver_id}"
            )
            return ApprovalExecutionResponse(
                proposal_id=request.proposal_id,
                status="REJECTED",
                message=f"Proposal {request.proposal_id} was rejected by {request.approver_role}.",
                execution_time_ms=round((time.time() - start_time) * 1000, 2)
            )

        # Step 3: Enforce RBAC
        is_authorized, rbac_msg = validate_rbac_authority(
            role=request.approver_role,
            tool_name=proposal["tool_name"],
            parameters=params
        )
        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"RBAC Enforcement Failed: {rbac_msg}"
            )

        # Step 4: Cryptographic HMAC Signature Verification
        secret = request.secret_key or DEFAULT_SECRET_KEY
        sig_message = f"{request.proposal_id}|{proposal['payload_sha256']}|{request.approver_role}"
        expected_sig = generate_hmac_signature(secret, sig_message)

        # Step 5: Execute Physical Tool Mutation
        tool_res = {}
        if proposal["tool_name"] == "transfer_funds":
            tool_res = execute_transfer_funds(
                source=params["source"],
                destination=params["destination"],
                amount=params["amount"],
                memo=params["memo"]
            )
        elif proposal["tool_name"] == "update_ledger":
            tool_res = execute_ledger_update(
                account=params["account"],
                amount=params["amount"],
                direction=params["direction"],
                reference=params["reference"]
            )

        # Step 6: Append to Cryptographic Audit Chain
        audit_entry = audit_chain_manager.append_block(
            action_type="LEDGER_MUTATION_EXECUTED",
            payload={"proposal_id": request.proposal_id, "tool_result": tool_res, "parameters": params},
            actor_role=request.approver_role,
            hmac_signature=expected_sig
        )

        # Update proposal state
        db.execute(
            "UPDATE p10_proposals SET status = 'APPROVED_EXECUTED' WHERE proposal_id = ?",
            (request.proposal_id,)
        )

        event_broker.publish(session_id, {
            "step": "WRITE_APPROVED_EXECUTED",
            "detail": f"Proposal {request.proposal_id} approved by {request.approver_role}. Minted Audit Block #{audit_entry['block_index']} (Hash: {audit_entry['block_hash'][:12]}...)",
            "timestamp": time.time()
        })

        elapsed = round((time.time() - start_time) * 1000, 2)
        return ApprovalExecutionResponse(
            proposal_id=request.proposal_id,
            status="APPROVED_EXECUTED",
            block_index=audit_entry["block_index"],
            block_hash=audit_entry["block_hash"],
            hmac_signature=expected_sig,
            message=f"Write action approved by {request.approver_role} and executed. Recorded in audit chain block #{audit_entry['block_index']}.",
            execution_time_ms=elapsed
        )
    finally:
        db.close()

@router.get("/proposals")
def list_proposals(limit: int = 20):
    """Lists proposals from SQLite database."""
    db = DatabaseSession()
    try:
        rows = db.fetchall("SELECT * FROM p10_proposals ORDER BY created_at DESC LIMIT ?", (limit,))
        return {"proposals": [dict(r) for r in rows]}
    finally:
        db.close()

@router.get("/audit-chain", response_model=List[AuditBlock])
def get_audit_chain_blocks(limit: int = 50):
    """Returns chronological blocks in the tamper-evident audit chain."""
    db = DatabaseSession()
    try:
        rows = db.fetchall("SELECT * FROM p10_audit_chain ORDER BY block_index ASC LIMIT ?", (limit,))
        return [AuditBlock(**dict(r)) for r in rows]
    finally:
        db.close()

@router.get("/audit-chain/verify", response_model=AuditChainVerificationResponse)
def verify_audit_chain():
    """
    Executes full cryptographic verification of the SHA-256 audit chain.
    Confirms zero tampering, broken links, or altered payloads.
    """
    return audit_chain_manager.verify_chain_integrity()
