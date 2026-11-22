"""
Multi-Agent Implementation for Real Estate Sales Automation
Agent 1: LeadQualifierAgent
Agent 2: PropertyMatcherAgent
Agent 3: OfferDrafterAgent
"""
import os
import json
import uuid
from typing import Dict, Any, List
from .models import Lead, QualificationReport, PropertyMatch, DraftOffer

class LeadQualifierAgent:
    """Agent 1: Evaluates buyer budget, pre-approval, timeline, and intent."""
    def __init__(self):
        self.agent_name = "Agent 1: Lead Qualifier"

    def process(self, lead: Lead) -> QualificationReport:
        # Heuristic & Semantic evaluation (works offline and can be connected to LLM)
        score = 50
        strengths = []
        risks = []

        # 1. Budget analysis
        if lead.budget_max >= 500000:
            score += 20
            strengths.append(f"Substantial buying power (${lead.budget_max:,.0f} ceiling)")
        elif lead.budget_max >= 250000:
            score += 10
            strengths.append(f"Moderate budget range (${lead.budget_max:,.0f})")
        else:
            score -= 15
            risks.append(f"Sub-market budget for target areas (${lead.budget_max:,.0f})")

        # 2. Financing & Pre-approval
        if lead.pre_approved:
            score += 20
            strengths.append("Reported mortgage pre-approval / Cash buyer capability")
        else:
            score -= 10
            risks.append("No mortgage pre-approval documented yet")

        # 3. Timeline urgency
        timeline_lower = lead.timeline.lower()
        if any(w in timeline_lower for w in ["immediate", "cash", "30", "45", "asap"]):
            score += 15
            strengths.append(f"High purchase urgency ({lead.timeline})")
            urgency = "High"
        elif any(w in timeline_lower for w in ["casual", "not sure", "browsing", "year"]):
            score -= 20
            risks.append("Extended / Non-committal timeline")
            urgency = "Low"
        else:
            urgency = "Medium"

        # Determine final status
        score = max(5, min(98, score))
        if score >= 75:
            status = "HOT"
            intent = "High-Intent Active Buyer"
            rec_action = "Fast-track property matching & immediate broker outreach"
        elif score >= 50:
            status = "WARM"
            intent = "Qualified Explorer"
            rec_action = "Present top 2 matches with soft engagement cadence"
        else:
            status = "COLD"
            intent = "Passive Browser / Unqualified"
            rec_action = "Route to automated educational email drip; do not expend manual agent hours"

        notes = (
            f"Lead evaluated from {lead.source}. Buyer {lead.name} expresses desire for {lead.bedrooms_needed} BR "
            f"in {lead.desired_location}. Financing certainty is {'High' if lead.pre_approved else 'Unverified'}."
        )

        return QualificationReport(
            lead_id=lead.lead_id,
            qualification_status=status,
            score=score,
            buyer_intent=intent,
            budget_feasibility="Well-Aligned" if score >= 60 else "Tight/Misaligned",
            urgency_level=urgency,
            key_strengths=strengths,
            risk_factors=risks,
            qualifier_notes=notes,
            recommended_action=rec_action
        )


class PropertyMatcherAgent:
    """Agent 2: Researches internal property inventory to find top matches."""
    def __init__(self, properties_path: str = None):
        self.agent_name = "Agent 2: Property Matcher"
        if properties_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            properties_path = os.path.join(base_dir, "data", "properties.json")
        self.properties_path = properties_path
        self.inventory = self._load_inventory()

    def _load_inventory(self) -> List[Dict[str, Any]]:
        with open(self.properties_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def process(self, lead: Lead, qual: QualificationReport) -> List[PropertyMatch]:
        matched = []
        for prop in self.inventory:
            match_score = 40
            reasons = []

            # 1. Budget Fit
            price = prop["price"]
            if price <= lead.budget_max and price >= lead.budget_min:
                match_score += 30
                reasons.append(f"Price (${price:,.0f}) is perfectly inside lead's target range")
            elif price <= lead.budget_max * 1.1:
                match_score += 15
                reasons.append(f"Price (${price:,.0f}) is within 10% flexible range")
            else:
                match_score -= 20

            # 2. Location Fit
            if lead.desired_location.lower() in prop["location"].lower() or prop["location"].lower() in lead.desired_location.lower():
                match_score += 25
                reasons.append(f"Prime location match in {prop['location']}")
            else:
                match_score += 5
                reasons.append(f"Nearby district ({prop['location']})")

            # 3. Bedroom Fit
            if prop["bedrooms"] >= lead.bedrooms_needed:
                match_score += 15
                reasons.append(f"Meets bedroom requirement ({prop['bedrooms']} Beds vs {lead.bedrooms_needed} requested)")
            else:
                match_score -= 10

            # Concession idea
            concessions = "Standard seller closing assistance (up to $5,000) or 1-year home warranty."
            if match_score >= 80:
                concessions = "Exclusive VIP buyer incentive: $7,500 rate buy-down credit included."

            match_score = max(10, min(99, match_score))
            matched.append(PropertyMatch(
                property_id=prop["id"],
                title=prop["title"],
                price=prop["price"],
                location=prop["location"],
                match_score=match_score,
                match_reasons=reasons,
                concessions_suggested=concessions
            ))

        # Sort by match_score descending
        matched.sort(key=lambda x: x.match_score, reverse=True)
        return matched[:3]


class OfferDrafterAgent:
    """Agent 3: Drafts persuasive, personalized offer proposals and WhatsApp teasers."""
    def __init__(self):
        self.agent_name = "Agent 3: Offer Drafter"

    def process(self, lead: Lead, qual: QualificationReport, top_match: PropertyMatch) -> DraftOffer:
        offer_id = f"OFFER-{uuid.uuid4().hex[:6].upper()}"
        
        # Determine pricing strategy
        if qual.qualification_status == "HOT":
            proposed_price = top_match.price * 0.98  # 2% discount incentive for fast closing
            incentive = "2% Fast-Close Incentive + $5,000 Broker Closing Credit + Priority Title Escrow"
        else:
            proposed_price = top_match.price
            incentive = "Complimentary 1-Year Premium Home Warranty + Flexible Inspection Window"

        headline = f"Exclusive Preview & Acquisition Offer: {top_match.title}"
        
        formal_letter = (
            f"Dear {lead.name},\n\n"
            f"Thank you for contacting our agency regarding your property search in {lead.desired_location}.\n"
            f"Based on your requirements for a {lead.bedrooms_needed}-bedroom property and your verified buying profile, "
            f"our advisory team has secured an exclusive acquisition allocation for:\n\n"
            f"🏡 Property: {top_match.title} ({top_match.location})\n"
            f"💵 Listed Value: ${top_match.price:,.0f}\n"
            f"🏷️ Proposed Client Acquisition Price: ${proposed_price:,.0f}\n"
            f"🎁 Included Concession Package: {incentive}\n\n"
            f"Key Highlights:\n"
            + "\n".join([f" • {r}" for r in top_match.match_reasons]) + "\n\n"
            f"This proposal has been pre-screened by our acquisitions desk and is ready for your formal contract review.\n\n"
            f"Warm regards,\n"
            f"Acquisitions & Portfolio Management Team\n"
            f"Apex Horizon Real Estate Advisory"
        )

        whatsapp_teaser = (
            f"Hello {lead.name}! 🌟 Great news regarding your property search for {lead.desired_location}.\n\n"
            f"Our AI matching team just unlocked a private listing for you:\n"
            f"📍 *{top_match.title}*\n"
            f"💰 Price: *${proposed_price:,.0f}* (Special preview terms)\n"
            f"✨ Includes: {incentive}\n\n"
            f"Would you like our senior broker to walk you through the private floorplan and video tour today? 📲"
        )

        return DraftOffer(
            offer_id=offer_id,
            lead_id=lead.lead_id,
            property_id=top_match.property_id,
            headline=headline,
            proposed_price=proposed_price,
            incentive_package=incentive,
            formal_offer_letter=formal_letter,
            whatsapp_teaser=whatsapp_teaser,
            expires_in_days=7
        )
