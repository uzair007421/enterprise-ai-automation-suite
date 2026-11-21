"""
Cryptographic Human Approval Gate & RBAC Validator
Guarantees:
1. Every write proposal has an immutable SHA-256 payload digest.
2. Approval requires a cryptographically valid HMAC-SHA256 signature.
3. Role-Based Access Control (RBAC):
   - ANALYST: Cannot approve write operations.
   - MANAGER: Can approve up to $10,000.00.
   - CFO: Required for any transaction >= $10,000.00.
"""
import hmac
import hashlib
import json
from typing import Dict, Any, Tuple

DEFAULT_SECRET_KEY = "finguard_secret_hmac_2026"

def hash_payload(payload: Dict[str, Any]) -> str:
    """Calculates canonical SHA-256 digest of tool call parameters."""
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def generate_hmac_signature(secret_key: str, message: str) -> str:
    """Generates HMAC-SHA256 hexadecimal signature."""
    return hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

def verify_hmac_signature(secret_key: str, message: str, signature: str) -> bool:
    """Constant-time verification of HMAC-SHA256 signature."""
    expected = generate_hmac_signature(secret_key, message)
    return hmac.compare_digest(expected, signature)

def validate_rbac_authority(
    role: str,
    tool_name: str,
    parameters: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Validates if user role has authority to execute or approve the action.
    """
    clean_role = role.strip().upper()
    amount = float(parameters.get("amount", 0.0))

    if clean_role == "ANALYST":
        return False, "Role 'ANALYST' has read-only access. Write actions require Manager or CFO authorization."

    if clean_role == "MANAGER":
        if amount >= 10000.00:
            return False, f"Manager limit is $10,000.00. Transaction of ${amount:,.2f} requires mandatory CFO authorization."
        return True, "Manager approval authorized."

    if clean_role == "CFO":
        return True, "Executive CFO approval authorized."

    return False, f"Unknown or unauthorized role: '{role}'"
