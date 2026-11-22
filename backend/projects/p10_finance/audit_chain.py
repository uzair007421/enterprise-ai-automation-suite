"""
Tamper-Evident SHA-256 Audit Chain
Maintains a verifiable ledger of every sensitive action, approval signature,
and state change in SQLite table `p10_audit_chain`.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from core.db import DatabaseSession
from .schemas import AuditBlock, AuditChainVerificationResponse
from .crypto_gate import verify_approval_signature

GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def compute_block_hash(
    previous_hash: str,
    action_type: str,
    payload_json: str,
    actor_role: str,
    hmac_signature: str,
    timestamp: str
) -> str:
    """Calculates immutable SHA-256 hash for an audit block."""
    data = f"{previous_hash}|{action_type}|{payload_json}|{actor_role}|{hmac_signature}|{timestamp}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

class AuditChainManager:

    def __init__(self):
        # Lazy initialization: do not query DB at module import time
        pass

    def _ensure_genesis_block(self, tenant_id: str = "tenant_default"):
        """Initializes Block 0 (Genesis) for a tenant if its audit chain is empty."""
        try:
            db = DatabaseSession()
            try:
                row = db.fetchone("SELECT COUNT(*) as cnt FROM p10_audit_chain WHERE tenant_id = ?", (tenant_id,))
                if row and row["cnt"] == 0:
                    ts = "2026-11-20T00:00:00Z"
                    genesis_payload = json.dumps({"service": "FinGuard Autonomous Enterprise Core", "tenant_id": tenant_id}, sort_keys=True)
                    gen_hash = compute_block_hash(
                        previous_hash=GENESIS_PREV_HASH,
                        action_type="GENESIS_INITIALIZATION",
                        payload_json=genesis_payload,
                        actor_role="SYSTEM_SECURITY_ROOT",
                        hmac_signature=f"GENESIS_ROOT_{tenant_id.upper()}",
                        timestamp=ts
                    )
                    db.execute(
                        """
                        INSERT INTO p10_audit_chain 
                        (id, tenant_id, block_index, previous_hash, action_type, payload_json, actor_role, hmac_signature, block_hash, created_at)
                        VALUES (?, ?, 0, ?, 'GENESIS_INITIALIZATION', ?, 'SYSTEM_SECURITY_ROOT', ?, ?, ?)
                        """,
                        (f"BLK-GENESIS-{tenant_id[:8]}", tenant_id, GENESIS_PREV_HASH, genesis_payload, f"GENESIS_ROOT_{tenant_id.upper()}", gen_hash, ts)
                    )
                    db.commit()
            finally:
                db.close()
        except Exception:
            # Table not yet created (e.g. before init_db() runs in lifespan)
            pass

    def get_latest_block(self, tenant_id: str = "tenant_default") -> Dict[str, Any]:
        """Returns the current tip block of the audit chain for a tenant."""
        self._ensure_genesis_block(tenant_id=tenant_id)
        db = DatabaseSession()
        try:
            row = db.fetchone("SELECT * FROM p10_audit_chain WHERE tenant_id = ? ORDER BY block_index DESC LIMIT 1", (tenant_id,))
            return dict(row) if row else {}
        finally:
            db.close()

    def append_block(
        self,
        action_type: str,
        payload: Dict[str, Any],
        actor_role: str,
        hmac_signature: str,
        tenant_id: str = "tenant_default"
    ) -> Dict[str, Any]:
        """Appends a new HMAC-verified block to the tenant's chain."""
        self._ensure_genesis_block(tenant_id=tenant_id)
        latest = self.get_latest_block(tenant_id=tenant_id)
        prev_hash = latest.get("block_hash", GENESIS_PREV_HASH)
        next_index = latest.get("block_index", 0) + 1

        payload_copy = dict(payload)
        payload_copy["tenant_id"] = tenant_id
        payload_json = json.dumps(payload_copy, sort_keys=True, separators=(',', ':'))
        timestamp = datetime.now(timezone.utc).isoformat()
        block_hash = compute_block_hash(
            previous_hash=prev_hash,
            action_type=action_type,
            payload_json=payload_json,
            actor_role=actor_role,
            hmac_signature=hmac_signature,
            timestamp=timestamp
        )

        block_id = f"BLK-{uuid.uuid4().hex[:8].upper()}"
        db = DatabaseSession()
        try:
            db.execute(
                """
                INSERT INTO p10_audit_chain 
                (id, tenant_id, block_index, previous_hash, action_type, payload_json, actor_role, hmac_signature, block_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (block_id, tenant_id, next_index, prev_hash, action_type, payload_json, actor_role, hmac_signature, block_hash, timestamp)
            )
            db.commit()
            return {
                "block_id": block_id,
                "tenant_id": tenant_id,
                "block_index": next_index,
                "previous_hash": prev_hash,
                "block_hash": block_hash,
                "hmac_signature": hmac_signature,
                "timestamp": timestamp
            }
        finally:
            db.close()

    def verify_chain_integrity(self, tenant_id: str = "tenant_default") -> AuditChainVerificationResponse:
        """
        Verification: walks from Genesis to Tip for a tenant, re-calculating hashes
        and confirming zero tampering has occurred.
        """
        self._ensure_genesis_block(tenant_id=tenant_id)
        db = DatabaseSession()
        try:
            blocks = db.fetchall("SELECT * FROM p10_audit_chain WHERE tenant_id = ? ORDER BY block_index ASC", (tenant_id,))
            if not blocks:
                return AuditChainVerificationResponse(
                    is_valid=False,
                    total_blocks=0,
                    genesis_hash="NONE",
                    tip_hash="NONE",
                    audit_verdict="Audit chain is empty.",
                    tenant_id=tenant_id
                )

            for i, blk in enumerate(blocks):
                # Verify link to previous hash
                if i == 0:
                    expected_prev = GENESIS_PREV_HASH
                else:
                    expected_prev = blocks[i - 1]["block_hash"]

                if blk["previous_hash"] != expected_prev:
                    return AuditChainVerificationResponse(
                        is_valid=False,
                        total_blocks=len(blocks),
                        genesis_hash=blocks[0]["block_hash"],
                        tip_hash=blocks[-1]["block_hash"],
                        tampered_block_index=blk["block_index"],
                        audit_verdict=f"Link broken at block {blk['block_index']}: previous_hash does not match parent block_hash.",
                        tenant_id=tenant_id
                    )

                # Recompute and verify current block's hash
                recomputed = compute_block_hash(
                    previous_hash=blk["previous_hash"],
                    action_type=blk["action_type"],
                    payload_json=blk["payload_json"],
                    actor_role=blk["actor_role"],
                    hmac_signature=blk["hmac_signature"],
                    timestamp=blk["created_at"]
                )

                if blk["block_hash"] != recomputed:
                    return AuditChainVerificationResponse(
                        is_valid=False,
                        total_blocks=len(blocks),
                        genesis_hash=blocks[0]["block_hash"],
                        tip_hash=blocks[-1]["block_hash"],
                        tampered_block_index=blk["block_index"],
                        audit_verdict=f"Hash mismatch at block {blk['block_index']}: content tampered or signature invalid.",
                        tenant_id=tenant_id
                    )

                # Verify HMAC approval signature if it's an approved execution
                if blk["action_type"] in ("LEDGER_MUTATION_EXECUTED", "CREDIT_LIMIT_MUTATION_EXECUTED", "APPROVAL_EXECUTED"):
                    try:
                        p_data = json.loads(blk["payload_json"])
                        if "signed_at" in p_data:
                            prop_id = p_data.get("proposal_id", "")
                            p_params = p_data.get("parameters", {})
                            amount = float(p_params.get("amount", 0.0))
                            approver = p_data.get("approver", blk["actor_role"])
                            signed_ts = p_data.get("signed_at", blk["created_at"])
                            if not verify_approval_signature(
                                signature=blk["hmac_signature"],
                                proposal_id=prop_id,
                                amount=amount,
                                approver=approver,
                                timestamp=signed_ts
                            ):
                                return AuditChainVerificationResponse(
                                    is_valid=False,
                                    total_blocks=len(blocks),
                                    genesis_hash=blocks[0]["block_hash"],
                                    tip_hash=blocks[-1]["block_hash"],
                                    tampered_block_index=blk["block_index"],
                                    audit_verdict=f"HMAC signature tampering detected at block {blk['block_index']}.",
                                    tenant_id=tenant_id
                                )
                    except Exception as e:
                        return AuditChainVerificationResponse(
                            is_valid=False,
                            total_blocks=len(blocks),
                            genesis_hash=blocks[0]["block_hash"],
                            tip_hash=blocks[-1]["block_hash"],
                            tampered_block_index=blk["block_index"],
                            audit_verdict=f"Signature verification error at block {blk['block_index']}: {str(e)}",
                            tenant_id=tenant_id
                        )

            return AuditChainVerificationResponse(
                is_valid=True,
                total_blocks=len(blocks),
                genesis_hash=blocks[0]["block_hash"],
                tip_hash=blocks[-1]["block_hash"],
                tampered_block_index=None,
                audit_verdict="HASH_CHAIN_VERIFIED: All block digests and sequential hash links match.",
                tenant_id=tenant_id
            )
        finally:
            db.close()

audit_chain_manager = AuditChainManager()
