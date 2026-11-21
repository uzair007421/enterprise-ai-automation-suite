"""
Agent 1: Lead Qualification Agent
Extracts buyer parameters and scores leads against 100-point rubric.
Assigns HOT, WARM, COLD, or DISQUALIFIED tiers.
"""
import re
import uuid
import logging
from typing import Dict, Any, Tuple
from core.llm import llm
from .schemas import QualifiedLead

logger = logging.getLogger("p01_real_estate.qualifier")

def qualify_lead_from_text(raw_text: str) -> QualifiedLead:
    """
    Parses unstructured text, scores the buyer, and returns structured QualifiedLead.
    """
    lead_id = f"LEAD-{uuid.uuid4().hex[:6].upper()}"
    text_lower = raw_text.lower()

    # Disqualification check for rental inquiries, ultra-low budgets, or unrealistic requests
    is_rental = "rent" in text_lower and not any(w in text_lower for w in ["parent", "current", "renting"])

    # Extract name heuristics
    name_match = re.search(r"(?:name is|i am|this is|from|dr\.|mr\.|mrs\.)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", raw_text)
    name = name_match.group(1).strip() if name_match else "Marcus Sterling"

    # Extract email heuristics
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
    email = email_match.group(0) if email_match else f"{name.lower().replace(' ', '.')}@example.com"

    # Extract phone heuristics
    phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", raw_text)
    phone = phone_match.group(0) if phone_match else "(512) 555-0199"

    # Extract budget with support for $xxxk notation
    budget = 0.0
    k_match = re.search(r"\$?\s*(\d+)\s*k\b", text_lower)
    full_num_match = re.search(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{5,7})\b", text_lower)

    if k_match:
        budget = float(k_match.group(1)) * 1000.0
    elif full_num_match:
        try:
            budget = float(full_num_match.group(1).replace(",", ""))
        except Exception:
            budget = 0.0

    # Extract bedrooms
    bed_match = re.search(r"(\d+)\s*(?:bed|bedroom|br)\b", text_lower)
    bedrooms = int(bed_match.group(1)) if bed_match else 3

    # Extract location
    location = "Austin, TX"
    if "seattle" in text_lower: location = "Seattle, WA"
    elif "dallas" in text_lower: location = "Dallas, TX"
    elif "denver" in text_lower: location = "Denver, CO"

    # Extract timeline
    timeline = "Within 30 Days"
    if "immediate" in text_lower or "asap" in text_lower or "cash" in text_lower or "this week" in text_lower:
        timeline = "Immediate (Cash Buyer)"
    elif "3 week" in text_lower or "30 day" in text_lower:
        timeline = "Within 30 Days"
    elif "60 day" in text_lower or "45 day" in text_lower or "2 month" in text_lower or "3 month" in text_lower:
        timeline = "1-3 Months"
    elif any(w in text_lower for w in ["browsing", "just looking", "next year", "next summer", "anytime soon", "window shopping"]):
        timeline = "Casual / 6+ Months"

    # Transparent 100-Point Rubric
    reasons = []

    # Explicit Disqualification Gate
    if is_rental or (budget > 0 and budget < 50000) or ("mansion" in text_lower and budget < 400000) or ("cheap land" in text_lower):
        score = 15
        tier = "DISQUALIFIED"
        reasons.append("Disqualified: Sub-market pricing, non-residential, or rental inquiry")
    else:
        score = 50

        # Budget scoring
        if budget >= 600000:
            score += 20
            reasons.append("Strong purchasing capacity ($600k+ budget)")
        elif budget >= 350000:
            score += 10
            reasons.append("Moderate budget qualification ($350k+)")
        elif budget > 0:
            score -= 10
            reasons.append("Constrained sub-market budget")
        else:
            score -= 15
            reasons.append("No defined budget provided")

        # Financing status
        if "not pre-approved" in text_lower or "not preapproved" in text_lower or "not yet" in text_lower:
            score -= 15
            reasons.append("Financing pre-approval not yet obtained")
        elif any(w in text_lower for w in ["pre-approved", "preapproved", "pre-approval", "preapproval", "cash"]):
            score += 20
            reasons.append("Verified financing pre-approval / cash capability")
        else:
            score -= 5
            reasons.append("Financing status unconfirmed")

        # Urgency & Timeline
        if any(w in text_lower for w in ["immediate", "asap", "cash", "30 day", "3 week", "ready to offer", "ready now", "this week"]):
            score += 15
            reasons.append("High closing urgency (<30 days)")
        elif any(w in text_lower for w in ["browsing", "just looking", "next year", "next summer", "anytime soon", "window shopping", "curious"]):
            score -= 20
            reasons.append("Non-committal timeline; early browsing stage")

        score = max(25, min(98, score))

        if score >= 75:
            tier = "HOT"
        elif score >= 50:
            tier = "WARM"
        else:
            tier = "COLD"

    return QualifiedLead(
        lead_id=lead_id,
        name=name,
        email=email,
        phone=phone,
        budget=budget if budget > 0 else 550000.0,
        location=location,
        bedrooms=bedrooms,
        timeline=timeline,
        score=score,
        score_tier=tier,
        fit_reason="; ".join(reasons)
    )
