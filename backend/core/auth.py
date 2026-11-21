"""
Authentication & Authorization Module
Zero-dependency HMAC-SHA256 signed JWT tokens for Demo and Admin sessions.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status
from .config import settings

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode((data + padding).encode('utf-8'))

def create_access_token(payload: Dict[str, Any], expires_in_seconds: int = 3600) -> str:
    """Creates an HMAC-SHA256 signed JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(payload)
    body["exp"] = int(time.time()) + expires_in_seconds

    header_b64 = _base64url_encode(json.dumps(header).encode('utf-8'))
    body_b64 = _base64url_encode(json.dumps(body).encode('utf-8'))
    message = f"{header_b64}.{body_b64}".encode('utf-8')

    signature = hmac.new(settings.SECRET_KEY.encode('utf-8'), message, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{body_b64}.{sig_b64}"

def verify_access_token(token: str) -> Dict[str, Any]:
    """Verifies token integrity and expiration. Returns payload dictionary."""
    parts = token.split('.')
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")

    header_b64, body_b64, sig_b64 = parts
    message = f"{header_b64}.{body_b64}".encode('utf-8')

    expected_sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), message, hashlib.sha256).digest()
    actual_sig = _base64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    payload = json.loads(_base64url_decode(body_b64).decode('utf-8'))
    if payload.get("exp", 0) < time.time():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")

    return payload

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Dependency extracting verified user claims from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        # For public demo sandboxes, return default demo visitor role
        return {"sub": "guest_demo_user", "role": "demo_user"}

    token = authorization.split(" ")[1]
    return verify_access_token(token)

def require_role(required_role: str):
    """Dependency factory restricting endpoints by RBAC role."""
    def role_checker(user: Dict[str, Any] = Header(None)):
        if user.get("role") != required_role and user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires role '{required_role}'."
            )
        return user
    return role_checker
