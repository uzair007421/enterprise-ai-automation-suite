"""
Project 08: SSRF-Safe Web Crawler
Safely fetches competitor landing pages and pricing tables.
Enforces strict anti-SSRF protections, blocking localhost, private subnets, and metadata endpoints.
"""
import logging
from typing import Tuple
import httpx
from core.security import validate_url_ssrf_safety

logger = logging.getLogger("p08_competitor.crawler")

def fetch_competitor_html_safe(url: str) -> Tuple[bool, str]:
    """
    Validates URL safety against SSRF and fetches HTML content with strict size and timeout caps.
    """
    # 1. SSRF Gate
    is_safe = validate_url_ssrf_safety(url)
    if not is_safe:
        logger.warning(f"SSRF violation blocked for URL: {url}")
        return False, "SSRF_VIOLATION_BLOCKED: Target host resolved to a private, loopback, or metadata subnet."

    # 2. Safe HTTP Fetch
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=8.0, follow_redirects=False) as client:
            res = client.get(url, headers=headers)
            if res.status_code == 200:
                # Cap at 2MB
                return True, res.text[:2 * 1024 * 1024]
            elif 300 <= res.status_code < 400:
                # Redirects require independent SSRF re-validation
                redirect_url = res.headers.get("Location")
                return False, f"REDIRECT_NOT_FOLLOWED: Target requested redirect to {redirect_url}. Follow redirects disabled for SSRF safety."
            else:
                return False, f"HTTP_ERROR_{res.status_code}: Competitor server returned {res.status_code}"
    except Exception as e:
        logger.error(f"Failed to crawl competitor URL {url}: {e}")
        return False, f"CRAWL_FAILED: {str(e)}"
