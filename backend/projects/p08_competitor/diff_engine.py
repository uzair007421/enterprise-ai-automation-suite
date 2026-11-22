"""
Project 08: DOM Diffing & Strategic Intelligence Engine
Analyzes structural changes between competitor snapshots, categorizes change types,
and assigns 1-10 strategic impact scores.
"""
import uuid
import re
import difflib
import datetime
from typing import List, Tuple
from .schemas import CompetitorDiffItem

def strip_html_tags(html: str) -> str:
    """Strips HTML formatting tags, returning normalized readable text lines."""
    clean = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL)
    clean = re.sub(r"<script.*?</script>", "", clean, flags=re.DOTALL)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def extract_competitor_diffs(competitor: str, url: str, old_html: str, new_html: str) -> List[CompetitorDiffItem]:
    """
    Computes semantic differences between previous and current snapshots.
    Categorizes into PRICING_CHANGE, FEATURE_LAUNCH, POSITIONING_SHIFT, or DOCS_UPDATE.
    Returns empty list if snapshots are identical.
    """
    old_text = strip_html_tags(old_html) if old_html else ""
    new_text = strip_html_tags(new_html) if new_html else ""

    # Identical snapshots produce empty diff
    if old_text == new_text:
        return []

    diffs = []
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_lower = new_text.lower()
    old_lower = old_text.lower()

    # 1. Pricing Shift Detection
    price_indicators = ["$", "per month", "/mo", "annual", "pricing", "tier", "billing", "free tier", "enterprise quote"]
    old_prices = set(re.findall(r"\$\d+(?:\.\d{2})?(?:/mo)?", old_text))
    new_prices = set(re.findall(r"\$\d+(?:\.\d{2})?(?:/mo)?", new_text))

    if old_prices != new_prices or (any(w in new_lower for w in ["free tier", "unlimited"]) and not any(w in old_lower for w in ["free tier", "unlimited"])):
        diff_id = f"DIFF-{uuid.uuid4().hex[:6].upper()}"
        added_prices = new_prices - old_prices
        dropped_prices = old_prices - new_prices
        details = f"Pricing structure modified. Previous tiers: {', '.join(old_prices) or 'Standard'}. New tiers: {', '.join(new_prices) or 'Updated'}."
        if added_prices:
            details += f" Added: {', '.join(added_prices)}."
        if dropped_prices:
            details += f" Retired: {', '.join(dropped_prices)}."

        diffs.append(CompetitorDiffItem(
            diff_id=diff_id,
            competitor_name=competitor,
            change_type="PRICING_CHANGE",
            headline=f"Aggressive Pricing Adjustment Detected ({competitor})",
            details=details,
            impact_score=9,
            source_url=url,
            detected_at=now_str
        ))

    # 2. Feature Launch Detection
    feature_keywords = ["webhook", "sdk", "vector search", "soc2", "sso", "ai copilot", "real-time", "integration", "zapier", "slack"]
    new_features = [k for k in feature_keywords if k in new_lower and k not in old_lower]
    if new_features:
        diff_id = f"DIFF-{uuid.uuid4().hex[:6].upper()}"
        diffs.append(CompetitorDiffItem(
            diff_id=diff_id,
            competitor_name=competitor,
            change_type="FEATURE_LAUNCH",
            headline=f"New Capability Shipped: {', '.join(new_features).title()}",
            details=f"{competitor} added product features: {', '.join(new_features)}. Expanded product surface.",
            impact_score=8,
            source_url=url,
            detected_at=now_str
        ))

    # 3. Positioning / Messaging Shift
    positioning_keywords = ["enterprise-first", "autonomous", "governance", "security", "ai-native", "all-in-one"]
    new_positioning = [k for k in positioning_keywords if k in new_lower and k not in old_lower]
    if new_positioning:
        diff_id = f"DIFF-{uuid.uuid4().hex[:6].upper()}"
        diffs.append(CompetitorDiffItem(
            diff_id=diff_id,
            competitor_name=competitor,
            change_type="POSITIONING_SHIFT",
            headline=f"Brand Repositioning: '{new_positioning[0].title()}'",
            details=f"{competitor} adjusted primary marketing narrative toward {', '.join(new_positioning)}.",
            impact_score=6,
            source_url=url,
            detected_at=now_str
        ))

    # Fallback to minor docs update if text changed but no major category triggered
    if not diffs and old_text != new_text:
        diff_id = f"DIFF-{uuid.uuid4().hex[:6].upper()}"
        diffs.append(CompetitorDiffItem(
            diff_id=diff_id,
            competitor_name=competitor,
            change_type="DOCS_UPDATE",
            headline="Minor Documentation / Content Refresh",
            details="Incremental copy updates detected on landing page without strategic pricing or feature shifts.",
            impact_score=3,
            source_url=url,
            detected_at=now_str
        ))

    return diffs
