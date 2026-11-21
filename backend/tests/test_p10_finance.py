"""
Project 10: FinGuard Financial Agent & Cryptographic Approval Gate Test Suite
Verifies:
- ReAct tool calling: Autonomous read vs suspended write actions
- Human Cryptographic Write Gate: Mandatory proposal suspension
- Strict RBAC: Analyst (403), Manager (capped at $10k), CFO (unlimited)
- Tamper-Evident SHA-256 Audit Chain: Merkle link integrity and tamper detection
"""
import pytest
from fastapi import HTTPException
from projects.p10_finance.schemas import AgentQueryRequest, ApprovalExecutionRequest
from projects.p10_finance.router import (
    execute_agent_query,
    approve_write_action,
    verify_audit_chain,
    get_audit_chain_blocks
)
from core.db import DatabaseSession

def test_autonomous_read_tool_execution():
    """Verify read tools execute autonomously without human suspension."""
    req = AgentQueryRequest(
        query="What is our current treasury balance across accounts?",
        user_id="analyst_alice",
        role="ANALYST"
    )
    resp = execute_agent_query(req)
    assert resp.tool_proposal is not None
    assert resp.tool_proposal.tool_type == "READ"
    assert resp.tool_proposal.requires_human_approval is False
    assert resp.tool_proposal.status == "EXECUTED_AUTONOMOUSLY"
    assert "Operating Account" in resp.direct_answer

def test_write_action_interception_and_suspension():
    """Verify write actions are strictly intercepted into PENDING_HUMAN_APPROVAL."""
    req = AgentQueryRequest(
        query="Transfer $5,000 to Amazon Web Services for infrastructure invoice",
        user_id="analyst_bob",
        role="ANALYST"
    )
    resp = execute_agent_query(req)
    assert resp.tool_proposal is not None
    assert resp.tool_proposal.tool_type == "WRITE"
    assert resp.tool_proposal.requires_human_approval is True
    assert resp.tool_proposal.status == "PENDING_HUMAN_APPROVAL"
    assert len(resp.tool_proposal.payload_sha256) == 64
    assert resp.tool_proposal.proposal_id.startswith("PROP-WRITE-")

def test_rbac_analyst_cannot_approve():
    """Verify an Analyst attempting to approve a write action is blocked with 403 Forbidden."""
    # Formulate proposal
    q_req = AgentQueryRequest(query="Transfer $2,500 to vendor", user_id="analyst_1", role="ANALYST")
    q_resp = execute_agent_query(q_req)
    prop_id = q_resp.tool_proposal.proposal_id

    # Analyst tries to approve
    app_req = ApprovalExecutionRequest(
        proposal_id=prop_id,
        approver_id="analyst_1",
        approver_role="ANALYST",
        decision="APPROVE"
    )
    with pytest.raises(HTTPException) as exc_info:
        approve_write_action(app_req)
    assert exc_info.value.status_code == 403
    assert "read-only" in exc_info.value.detail.lower()

def test_rbac_manager_approval_under_10k_succeeds():
    """Verify a Manager can approve a transfer under $10,000."""
    q_req = AgentQueryRequest(query="Transfer $4,000 to vendor", user_id="analyst_1", role="ANALYST")
    q_resp = execute_agent_query(q_req)
    prop_id = q_resp.tool_proposal.proposal_id

    app_req = ApprovalExecutionRequest(
        proposal_id=prop_id,
        approver_id="manager_dave",
        approver_role="MANAGER",
        decision="APPROVE"
    )
    res = approve_write_action(app_req)
    assert res.status == "APPROVED_EXECUTED"
    assert res.block_index is not None
    assert len(res.block_hash) == 64

def test_rbac_manager_over_10k_blocked_requires_cfo():
    """Verify a Manager attempting to approve >= $10,000 is blocked, but CFO succeeds."""
    q_req = AgentQueryRequest(query="Transfer $25,000 to vendor", user_id="analyst_1", role="ANALYST")
    q_resp = execute_agent_query(q_req)
    prop_id = q_resp.tool_proposal.proposal_id

    # Manager attempt -> 403 Forbidden
    mgr_req = ApprovalExecutionRequest(
        proposal_id=prop_id,
        approver_id="manager_dave",
        approver_role="MANAGER",
        decision="APPROVE"
    )
    with pytest.raises(HTTPException) as exc_info:
        approve_write_action(mgr_req)
    assert exc_info.value.status_code == 403
    assert "CFO authorization" in exc_info.value.detail

    # CFO attempt -> 200 OK
    cfo_req = ApprovalExecutionRequest(
        proposal_id=prop_id,
        approver_id="cfo_elena",
        approver_role="CFO",
        decision="APPROVE"
    )
    res = approve_write_action(cfo_req)
    assert res.status == "APPROVED_EXECUTED"
    assert res.block_index is not None

def test_cryptographic_audit_chain_tamper_detection():
    """Verify the audit chain mathematically detects any unauthorized tampering."""
    # Ensure chain has valid blocks
    verification = verify_audit_chain()
    assert verification.is_valid is True
    assert verification.total_blocks >= 1

    # Simulate adversarial database tamper
    db = DatabaseSession()
    try:
        # Tamper with the tip block
        tip = db.fetchone("SELECT * FROM p10_audit_chain ORDER BY block_index DESC LIMIT 1")
        original_hash = tip["block_hash"]
        fake_hash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        db.execute("UPDATE p10_audit_chain SET block_hash = ? WHERE id = ?", (fake_hash, tip["id"]))

        # Chain verification MUST fail
        tampered_verify = verify_audit_chain()
        assert tampered_verify.is_valid is False
        assert tampered_verify.tampered_block_index == tip["block_index"]

        # Restore original block hash to maintain clean test state
        db.execute("UPDATE p10_audit_chain SET block_hash = ? WHERE id = ?", (original_hash, tip["id"]))

        # Re-verify restored chain
        restored_verify = verify_audit_chain()
        assert restored_verify.is_valid is True
    finally:
        db.close()
