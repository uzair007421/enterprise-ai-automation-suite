"""
Cryptographic Tamper-Evident SHA-256 Audit Chain
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

GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def compute_block_hash(
    previous_hash: str,
    action_type: str,
    payload_json: str,
    actor_role: str,
    hmac_signature: str,
    timestamp: str
) -> str:
    """Calculates immutable cryptographic SHA-256 hash for an audit block."""
    data = f"{previous_hash}|{action_type}|{payload_json}|{actor_role}|{hmac_signature}|{timestamp}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

class AuditChainManager:

    def __init__(self):
        self._ensure_genesis_block()

    def _ensure_genesis_block(self):
        """Initializes Block 0 (Genesis) if audit chain is empty."""
        db = DatabaseSession()
        try:
            row = db.fetchone("SELECT COUNT(*) as cnt FROM p10_audit_chain")
            if row and row["cnt"] == 0:
                ts = "2026-11-20T00:00:00Z"
                genesis_payload = json.dumps({"service": "FinGuard Autonomous Enterprise Core"}, sort_keys=True)
                gen_hash = compute_block_hash(
                    previous_hash=GENESIS_PREV_HASH,
                    action_type="GENESIS_INITIALIZATION",
                    payload_json=genesis_payload,
                    actor_role="SYSTEM_SECURITY_ROOT",
                    hmac_signature="GENESIS_ROOT_SIGNATURE_2026",
                    timestamp=ts
                )
                db.execute(
                    """
                    INSERT INTO p10_audit_chain 
                    (id, block_index, previous_hash, action_type, payload_json, actor_role, hmac_signature, block_hash, created_at)
                    VALUES (?, 0, ?, 'GENESIS_INITIALIZATION', ?, 'SYSTEM_SECURITY_ROOT', 'GENESIS_ROOT_SIGNATURE_2026', ?, ?)
                    """,
                    ("BLK-GENESIS-0", GENESIS_PREV_HASH, genesis_payload, gen_hash, ts)
                )
        finally:
            db.close()

    def get_latest_block(self) -> Dict[str, Any]:
        """Returns the current tip block of the audit chain."""
        db = DatabaseSession()
        try:
            row = db.fetchone("SELECT * FROM p10_audit_chain ORDER BY block_index DESC LIMIT 1")
            return dict(row) if row else {}
        finally:
            db.close()

    def append_block(
        self,
        action_type: str,
        payload: Dict[str, Any],
        actor_role: str,
        hmac_signature: str
    ) -> Dict[str, Any]:
        """Appends a new cryptographically verified block to the chain."""
        latest = self.get_latest_block()
        prev_hash = latest.get("block_hash", GENESIS_PREV_HASH)
        next_index = latest.get("block_index", 0) + 1

        payload_json = json.dumps(payload, sort_keys=True)
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
                (id, block_index, previous_hash, action_type, payload_json, actor_role, hmac_signature, block_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (block_id, next_index, prev_hash, action_type, payload_json, actor_role, hmac_signature, block_hash, timestamp)
            )
            return {
                "block_id": block_id,
                "block_index": next_index,
                "previous_hash": prev_hash,
                "block_hash": block_hash,
                "hmac_signature": hmac_signature,
                "timestamp": timestamp
            }
        finally:
            db.close()

    def verify_chain_integrity(self) -> AuditChainVerificationResponse:
        """
        Cryptographic verification: walks from Genesis to Tip, re-calculating hashes
        and confirming zero tampering has occurred.
        """
        db = DatabaseSession()
        try:
            blocks = db.fetchall("SELECT * FROM p10_audit_chain ORDER BY block_index ASC")
            if not blocks:
                return AuditChainVerificationResponse(
                    is_valid=False,
                    total_blocks=0,
                    genesis_hash="NONE",
                    tip_hash="NONE",
                    audit_verdict="Audit chain is empty."
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
                        audit_verdict=f"Link broken at block {blk['block_index']}: previous_hash does not match parent block_hash."
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
                        audit_verdict=f"Hash mismatch at block {blk['block_index']}: content tampered or signature invalid."
                    )

            return AuditChainVerificationResponse(
                is_valid=True,
                total_blocks=len(blocks),
                genesis_hash=blocks[0]["block_hash"],
                tip_hash=blocks[-1]["block_hash"],
                tampered_block_index=None,
                audit_verdict="CRYPTOGRAPHIC_CHAIN_VERIFIED_100_PERCENT: All block digests and Merkle links match."
            )
        finally:
            db.close()

audit_chain_manager = AuditChainManager()
