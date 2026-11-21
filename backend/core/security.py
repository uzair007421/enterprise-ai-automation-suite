"""
Core Security Module: SSRF Protection, Session Isolation & Rate Limiting
Enforces strict perimeter security for public demos.
"""
import ipaddress
import socket
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from fastapi import Request, HTTPException, status
from .config import settings

class SSRFProtection:
    """Validates URLs to prevent Server-Side Request Forgery against internal infrastructure."""

    BLOCKED_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),      # Loopback IPv4
        ipaddress.ip_network("::1/128"),           # Loopback IPv6
        ipaddress.ip_network("10.0.0.0/8"),       # Private RFC1918
        ipaddress.ip_network("172.16.0.0/12"),    # Private RFC1918
        ipaddress.ip_network("192.168.0.0/16"),   # Private RFC1918
        ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / Cloud Metadata (AWS/GCP/Azure)
        ipaddress.ip_network("fe80::/10"),        # Link-Local IPv6
        ipaddress.ip_network("fc00::/7"),         # Unique Local IPv6
        ipaddress.ip_network("0.0.0.0/8"),        # This host
        ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ]

    @classmethod
    def is_safe_url(cls, url: str) -> Tuple[bool, str]:
        """
        Validates URL scheme, hostname, and resolved IP addresses against private subnet blocklist.
        Returns (is_safe, error_reason).
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ["http", "https"]:
                return False, f"Invalid scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."

            hostname = parsed.hostname
            if not hostname:
                return False, "URL does not contain a valid hostname."

            # Disallow localhost keywords
            if hostname.lower() in ["localhost", "local", "127.0.0.1", "0.0.0.0", "metadata.google.internal"]:
                return False, "Targeting local hostnames is strictly forbidden."

            # Resolve DNS to check real destination IP
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)

                for blocked_net in cls.BLOCKED_NETWORKS:
                    if ip_obj in blocked_net:
                        return False, f"Resolved IP {ip_str} belongs to protected internal subnet ({blocked_net})."

            return True, "Safe"
        except Exception as e:
            return False, f"DNS resolution failed: {str(e)}"

def validate_url_ssrf_safety(url: str) -> bool:
    """Convenience helper returning boolean for SSRF safety."""
    is_safe, _ = SSRFProtection.is_safe_url(url)
    return is_safe

class RateLimiter:
    """Sliding window in-memory rate limiter per client IP and session."""

    def __init__(self, limit_per_minute: int = 30):
        self.limit = limit_per_minute
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - 60.0

        if client_id not in self.requests:
            self.requests[client_id] = [now]
            return True

        # Purge timestamps older than 60 seconds
        valid_timestamps = [t for t in self.requests[client_id] if t > window_start]
        self.requests[client_id] = valid_timestamps

        if len(valid_timestamps) >= self.limit:
            return False

        self.requests[client_id].append(now)
        return True

    def cleanup(self):
        """Periodically clean up stale client entries."""
        now = time.time()
        cutoff = now - 120.0
        stale_keys = [k for k, timestamps in self.requests.items() if not timestamps or timestamps[-1] < cutoff]
        for k in stale_keys:
            del self.requests[k]

rate_limiter = RateLimiter(limit_per_minute=settings.RATE_LIMIT_PER_MINUTE)

class SessionIsolationManager:
    """Manages ephemeral visitor demo sessions with automatic 1-hour TTL cleanup."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self.sessions: Dict[str, Dict[str, any]] = {}

    def get_or_create_session(self, session_id: str) -> Dict[str, any]:
        now = time.time()
        self.cleanup_expired()

        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": now,
                "last_active": now,
                "data": {}
            }
        else:
            self.sessions[session_id]["last_active"] = now

        return self.sessions[session_id]

    def cleanup_expired(self):
        now = time.time()
        expired = [sid for sid, s in self.sessions.items() if now - s["last_active"] > self.ttl]
        for sid in expired:
            del self.sessions[sid]

session_manager = SessionIsolationManager(ttl_seconds=settings.SESSION_TTL_SECONDS)

async def check_rate_limit(request: Request):
    """FastAPI Dependency for rate limiting requests."""
    client_ip = request.client.host if request.client else "unknown"
    session_id = request.headers.get("X-Session-ID", client_ip)

    if not rate_limiter.is_allowed(session_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded (30 requests/minute). Please wait 30 seconds."
        )
