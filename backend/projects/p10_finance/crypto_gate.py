"""
Cryptographic Human Approval Gate & RBAC Validator
Guarantees:
1. Every write proposal has an immutable SHA-256 payload digest.
2. Approval requires a cryptographically valid HMAC-SHA256 signature generated with server-held APPROVAL_SIGNING_KEY.
3. Role-Based Access Control (RBAC):
   - ANALYST: Cannot approve write operations.
   - MANAGER: Can approve up to $10,000.00.
   - CFO: Required for any transaction >= $10,000.00.
4. Canonical JSON separators (, and :) for signature deterministic serialization.
5. Standard RFC 7519 JWT issue/verify with zero external dependencies.
"""
import hmac
import hashlib
import json
import base64
import time
from typing import Dict, Any, Tuple, Optional
from core.config import settings

DEFAULT_SECRET_KEY = "finguard_secret_hmac_2026"

ACCOUNTS = {
    "analyst": {"password": "analyst123", "role": "ANALYST"},
    "manager": {"password": "mgr123", "role": "MANAGER"},
    "cfo": {"password": "cfo123", "role": "CFO"}
}

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def b64url_decode(data: str) -> bytes:
    rem = len(data) % 4
    if rem > 0:
        data += '=' * (4 - rem)
    return base64.urlsafe_b64decode(data.encode('utf-8'))

def create_access_token(user_id: str, role: str, expires_delta_seconds: int = 86400) -> str:
    """Generates standard HMAC-SHA256 JWT access token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time() + expires_delta_seconds)
    }
    hdr_b64 = b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    pay_b64 = b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f"{hdr_b64}.{pay_b64}"
    sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input.encode('utf-8'), hashlib.sha256).digest()
    return f"{signing_input}.{b64url_encode(sig)}"

def verify_access_token(token: str) -> Dict[str, Any]:
    """Decodes and cryptographically verifies JWT access token."""
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    signing_input = f"{parts[0]}.{parts[1]}"
    sig = b64url_decode(parts[2])
    expected_sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input.encode('utf-8'), hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("Invalid JWT signature")
    payload = json.loads(b64url_decode(parts[1]).decode('utf-8'))
    if "exp" in payload and time.time() > payload["exp"]:
        raise ValueError("JWT token expired")
    return payload

def hash_payload(payload: Dict[str, Any]) -> str:
    """Calculates canonical SHA-256 digest of tool call parameters using canonical separators."""
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def sign_approval(proposal_id: str, amount: float, approver: str, timestamp: str) -> str:
    """
    Generates HMAC-SHA256 signature using server-held APPROVAL_SIGNING_KEY over:
    id + amount + approver + timestamp using canonical JSON separators (, and :).
    """
    sign_obj = {
        "amount": round(float(amount), 2),
        "approver": approver,
        "id": proposal_id,
        "timestamp": timestamp
    }
    canonical_bytes = json.dumps(sign_obj, separators=(',', ':'), sort_keys=True).encode("utf-8")
    key = settings.APPROVAL_SIGNING_KEY.encode("utf-8")
    return hmac.new(key, canonical_bytes, hashlib.sha256).hexdigest()

def verify_approval_signature(signature: str, proposal_id: str, amount: float, approver: str, timestamp: str) -> bool:
    """Verifies HMAC-SHA256 signature of an approval against server-held APPROVAL_SIGNING_KEY."""
    expected = sign_approval(proposal_id, amount, approver, timestamp)
    return hmac.compare_digest(expected, signature)

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
