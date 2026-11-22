"""
Agent 1: Lead Qualification Agent
Extracts buyer parameters and scores leads against 100-point rubric.
Assigns HOT, WARM, COLD, INCOMPLETE_INQUIRY, or DISQUALIFIED tiers.
No hallucinated defaults for budget, bedrooms, timeline, or financing verification.
"""
import re
import uuid
import logging
from typing import Dict, Any, Tuple, Optional
from core.llm import llm
from .schemas import QualifiedLead

logger = logging.getLogger("p01_real_estate.qualifier")

def qualify_lead_from_text(raw_text: str, tenant_id: str = "default_brokerage") -> QualifiedLead:
    """
    Parses unstructured text, scores the buyer, and returns structured QualifiedLead.
    Eliminates imaginary defaults: preserves budget=0.0 and bedrooms=0 when unmentioned.
    """
    lead_id = f"LEAD-{uuid.uuid4().hex[:6].upper()}"
    text_lower = raw_text.lower()

    # Disqualification check for rental inquiries, student housing, or ultra-low budgets
    is_rental = (
        ("rent" in text_lower and not any(w in text_lower for w in ["currently rent", "renting currently", "stop renting", "tired of renting"])) or
        "student" in text_lower or
        "college" in text_lower or
        "dorm" in text_lower or
        "/mo" in text_lower or
        "/month" in text_lower or
        "per month" in text_lower
    )

    # Extract name heuristics
    name_match = re.search(r"(?:name is|i am|i'm|this is|from|buyer|reach|contact|dr\.|mr\.|mrs\.)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", raw_text, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip().title()
    else:
        first_line = raw_text.splitlines()[0].strip() if raw_text else ""
        line_match = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b", first_line)
        name = line_match.group(1).strip() if line_match else "Unspecified Lead"

    # Extract email heuristics
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", raw_text)
    email = email_match.group(0) if email_match else "N/A"

    # Extract phone heuristics
    phone_match = re.search(r"(?:\+?1[-.\s]*)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", raw_text)
    phone = phone_match.group(0) if phone_match else "N/A"

    # Extract budget: Support single values and ranges ($550k-600k, $500,000 - $650,000, $1M - $1.5M)
    budget = 0.0
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None

    # 1. Range Check: "$550k-600k", "$550k to $600k", "$500 - $600k"
    k_range_match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*k?\s*(?:-|to|–)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\s*k\b", text_lower)
    # 2. Range Check: "$1M - $1.5M", "$1 to $1.5 million"
    m_range_match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|million)?\s*(?:-|to|–)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|million)\b", text_lower)
    # 3. Range Check: "$500,000 to $650,000", "$500,000 - $650,000"
    full_range_match = re.search(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})+)\s*(?:-|to|–)\s*\$?\s*([0-9]{1,3}(?:,[0-9]{3})+)", text_lower)

    if k_range_match:
        val1 = float(k_range_match.group(1)) * 1000.0
        val2 = float(k_range_match.group(2)) * 1000.0
        budget_min = min(val1, val2)
        budget_max = max(val1, val2)
        budget = budget_max
    elif m_range_match:
        val1 = float(m_range_match.group(1)) * 1000000.0
        val2 = float(m_range_match.group(2)) * 1000000.0
        budget_min = min(val1, val2)
        budget_max = max(val1, val2)
        budget = budget_max
    elif full_range_match:
        val1 = float(full_range_match.group(1).replace(",", ""))
        val2 = float(full_range_match.group(2).replace(",", ""))
        budget_min = min(val1, val2)
        budget_max = max(val1, val2)
        budget = budget_max
    else:
        # Single value matches
        m_match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|million)\b", text_lower)
        k_match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*k\b", text_lower)
        full_num_match = re.search(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{5,8})\b", text_lower)
        mo_match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:\/mo|\/month|per\s+month)\b", text_lower)

        if m_match:
            budget = float(m_match.group(1)) * 1000000.0
        elif k_match:
            budget = float(k_match.group(1)) * 1000.0
        elif full_num_match:
            try:
                budget = float(full_num_match.group(1).replace(",", ""))
            except Exception:
                budget = 0.0
        elif mo_match:
            budget = float(mo_match.group(1))

    # Extract bedrooms - DO NOT default to 3 if unmentioned
    bed_match = re.search(r"\b(\d+)\s*(?:bed|bedroom|br)\b", text_lower)
    bedrooms = int(bed_match.group(1)) if bed_match else 0

    # Extract location
    location = "Unspecified Location"
    city_map = {
        "austin": "Austin, TX",
        "seattle": "Seattle, WA",
        "dallas": "Dallas, TX",
        "denver": "Denver, CO",
        "houston": "Houston, TX",
        "chicago": "Chicago, IL",
        "miami": "Miami, FL",
        "phoenix": "Phoenix, AZ",
        "san francisco": "San Francisco, CA",
        "new york": "New York, NY",
        "los angeles": "Los Angeles, CA",
        "atlanta": "Atlanta, GA",
        "boston": "Boston, MA"
    }
    for city_key, city_val in city_map.items():
        if city_key in text_lower:
            location = city_val
            break
    if location == "Unspecified Location":
        loc_match = re.search(r"(?:in|near|around)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s*,\s*[A-Z]{2})?)", raw_text)
        if loc_match:
            location = loc_match.group(1).strip()

    # Extract timeline - DO NOT default to "Within 30 Days" if unmentioned
    timeline = "Unspecified"
    if any(w in text_lower for w in ["immediate", "asap", "ready now", "this week", "this month"]):
        timeline = "Immediate (Ready Buyer)"
    elif any(w in text_lower for w in ["30 day", "within 30 days", "3 week", "next month"]):
        timeline = "Within 30 Days"
    elif any(w in text_lower for w in ["60 day", "45 day", "2 month", "3 month", "1-3 month"]):
        timeline = "1-3 Months"
    elif any(w in text_lower for w in ["browsing", "just looking", "next year", "next summer", "anytime soon", "window shopping"]):
        timeline = "Casual / 6+ Months"

    # Transparent 100-Point Rubric
    reasons = []

    # Explicit Disqualification Gate for rentals, students, or sub-market pricing
    if is_rental or (budget > 0 and budget < 50000) or ("mansion" in text_lower and budget < 400000) or ("cheap land" in text_lower):
        score = 20
        tier = "DISQUALIFIED"
        reasons.append("Disqualified: Sub-market pricing, non-residential, student housing, or rental inquiry (<40 score)")
    elif budget == 0.0 and location == "Unspecified Location" and bedrooms == 0:
        # Incomplete / bare inquiry (e.g. "I want a house")
        score = 25
        tier = "INCOMPLETE_INQUIRY"
        reasons.append("Incomplete lead parameters: missing budget, bedrooms, and target location")
    else:
        score = 40  # Baseline for residential buyer inquiries

        # Budget scoring
        if budget >= 1500000:
            score += 30
            if budget_min:
                reasons.append(f"Premier luxury purchasing range (${budget_min/1000000:.1f}M - ${budget_max/1000000:.1f}M)")
            else:
                reasons.append("Premier luxury purchasing capacity ($1.5M+ budget)")
        elif budget >= 1000000:
            score += 25
            if budget_min:
                reasons.append(f"High purchasing capacity range (${budget_min/1000000:.1f}M - ${budget_max/1000000:.1f}M)")
            else:
                reasons.append("High purchasing capacity ($1M+ budget)")
        elif budget >= 600000:
            score += 20
            if budget_min:
                reasons.append(f"Strong purchasing capacity range (${budget_min/1000:.0f}k - ${budget_max/1000:.0f}k)")
            else:
                reasons.append("Strong purchasing capacity ($600k+ budget)")
        elif budget >= 350000:
            score += 10
            if budget_min:
                reasons.append(f"Moderate budget qualification range (${budget_min/1000:.0f}k - ${budget_max/1000:.0f}k)")
            else:
                reasons.append("Moderate budget qualification ($350k+)")
        elif budget > 0:
            score -= 5
            reasons.append("Constrained sub-market budget")
        else:
            score -= 10
            reasons.append("No defined budget provided")

        # Financing status: Honest categorization (Cash claims are self-reported, not 'verified')
        if "not pre-approved" in text_lower or "not preapproved" in text_lower or "not yet" in text_lower or "no preapproval" in text_lower:
            score -= 15
            reasons.append("Financing pre-approval not yet obtained")
        elif any(w in text_lower for w in ["cash buyer", "all cash", "cash"]):
            score += 20
            reasons.append("Self-reported cash buyer capability (unverified proof of funds)")
        elif any(w in text_lower for w in ["pre-approved", "preapproved", "pre-approval", "preapproval", "approved buyer"]):
            score += 20
            reasons.append("Reported financing pre-approval")
        else:
            reasons.append("Financing status unconfirmed")

        # Urgency & Timeline
        if timeline == "Immediate (Ready Buyer)":
            score += 20
            reasons.append("High closing urgency (Immediate / this month)")
        elif timeline == "Within 30 Days":
            score += 15
            reasons.append("Standard 30-day closing timeline")
        elif timeline == "Casual / 6+ Months":
            score -= 25
            reasons.append("Non-committal timeline; early browsing stage")

        score = max(10, min(98, score))

        if score >= 75:
            tier = "HOT"
        elif score >= 50:
            tier = "WARM"
        else:
            tier = "COLD"

    return QualifiedLead(
        lead_id=lead_id,
        tenant_id=tenant_id,
        name=name,
        email=email,
        phone=phone,
        budget=budget,
        budget_min=budget_min,
        budget_max=budget_max,
        location=location,
        bedrooms=bedrooms,
        timeline=timeline,
        score=score,
        score_tier=tier,
        fit_reason="; ".join(reasons)
    )
