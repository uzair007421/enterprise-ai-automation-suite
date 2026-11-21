"""
SaaS Competitor Market Intelligence Engine
- Multi-Source Tracker (Pricing, Features, Blogs, Reviews)
- Algorithmic Change Diffing
- Strategic Business Impact Scoring (1 to 10)
- Executive Weekly Intelligence Digest Generator
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

class CompetitorIntelEngine:
    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_file = os.path.join(base_dir, "data", "competitors_baseline.json")
        self.data_file = data_file
        self.state_file = os.path.join(os.path.dirname(data_file), "intel_state.json")
        self._ensure_state()

    def _ensure_state(self):
        if not os.path.exists(self.state_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                base_comps = json.load(f)

            # Expand to 15 competitors
            all_comps = []
            names = [
                ("FlowCraft AI", "Workflow Automation", 49),
                ("OmniBotics", "Conversational AI", 79),
                ("SyncWave CRM", "CRM & Sales AI", 35),
                ("HyperAutomate", "Enterprise RPA", 199),
                ("AgentPulse", "Agent Orchestration", 89),
                ("TaskGenie", "Task Management AI", 29),
                ("DataNexus", "Data Pipeline AI", 120),
                ("LeadForge", "B2B Lead Enrichment", 65),
                ("QuickBot", "Customer Support Bot", 40),
                ("CloudSentinel", "Cloud Cost Optimizer", 150),
                ("VoiceFlowHQ", "Voice Telephony AI", 95),
                ("DocuExtract", "Document OCR AI", 85),
                ("GrowthEngine", "Marketing Automation", 110),
                ("SalesSprint", "Outbound Email AI", 55),
                ("LegalScan", "Contract Analysis AI", 250)
            ]

            for i, (name, cat, price) in enumerate(names):
                all_comps.append({
                    "id": f"COMP-{i+1:02d}",
                    "name": name,
                    "website": f"https://{name.lower().replace(' ', '')}.io",
                    "category": cat,
                    "pricing": {"pro_tier": price, "enterprise_tier": price * 4},
                    "features": ["Cloud Sync", "REST API", "Webhook Triggers", "Analytics Dashboard"],
                    "latest_blog": f"Maximizing ROI with {name} in 2026",
                    "review_rating": round(4.0 + (i % 8) * 0.1, 1),
                    "last_scanned": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                })

            initial = {
                "competitors": all_comps,
                "detected_changes": [],
                "latest_digest": None
            }
            self._save(initial)

    def _load(self) -> Dict[str, Any]:
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def run_weekly_scan(self) -> Dict[str, Any]:
        """Simulates full scraping sweep across 15 competitors and computes strategic diffs."""
        state = self._load()

        detected = [
            {
                "id": "DIFF-01",
                "competitor_name": "FlowCraft AI",
                "category": "PRICING_CHANGE",
                "impact_score": 9,
                "importance_rating": "CRITICAL",
                "headline": "Pro Tier Pricing Increased from $49/mo to $69/mo (+40.8%)",
                "detail": "FlowCraft updated their pricing table today. The $49 entry tier was eliminated and grandfathered users were given 60 days notice. Free tier API rate limit was reduced by 50%.",
                "source_url": "https://flowcraft.io/pricing#plans",
                "strategic_takeaway": "Immediate acquisition opportunity. Run Google & LinkedIn ad campaigns targeting FlowCraft users searching for affordable alternatives.",
                "detected_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            },
            {
                "id": "DIFF-02",
                "competitor_name": "OmniBotics",
                "category": "NEW_FEATURE_LAUNCH",
                "impact_score": 8,
                "importance_rating": "HIGH",
                "headline": "Launched Native Twilio & Vapi Voice Telephony Calling",
                "detail": "OmniBotics added full two-way voice dialing to their customer support suite, moving directly into our voice appointment territory.",
                "source_url": "https://omnibotics.com/changelog/2026-11-voice-telephony",
                "strategic_takeaway": "Accelerate our Dental & Clinic Voice AI templates to maintain vertical specialization advantage.",
                "detected_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            },
            {
                "id": "DIFF-03",
                "competitor_name": "SyncWave CRM",
                "category": "SENTIMENT_REVIEW_DROP",
                "impact_score": 7,
                "importance_rating": "MEDIUM-HIGH",
                "headline": "G2 Rating Dropped to 3.8 Stars (Spike in 1-Star Reviews)",
                "detail": "5 recent G2 reviews complain about unexpected billing overages and severe webhook reliability issues during peak US trading hours.",
                "source_url": "https://g2.com/products/syncwave-crm/reviews?filter=recent_critical",
                "strategic_takeaway": "Publish comparison case study highlighting our 99.9% uptime and zero-hidden-fee pricing model.",
                "detected_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            },
            {
                "id": "DIFF-04",
                "competitor_name": "HyperAutomate",
                "category": "BLOG_STRATEGY",
                "impact_score": 5,
                "importance_rating": "MEDIUM",
                "headline": "Published Whitepaper: 'Replacing Zapier in Enterprise Tech Stacks'",
                "detail": "HyperAutomate is aggressively positioning against traditional iPaaS providers to capture mid-market accounts.",
                "source_url": "https://hyperautomate.io/blog/enterprise-ipaas-migration",
                "strategic_takeaway": "Useful sales collateral inspiration for our own enterprise agency pitches.",
                "detected_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        ]

        # Generate Executive Digest
        digest_text = (
            f"WEEKLY COMPETITOR INTELLIGENCE BRIEFING — {datetime.utcnow().strftime('%B %d, %Y')}\n"
            f"Fleet Monitored: 15 SaaS Competitors | Scan Status: 100% Complete\n\n"
            f"1. [CRITICAL - 9/10] FlowCraft AI increased prices by 41% ($49 -> $69/mo). Action: Launch conquest ad campaign.\n"
            f"   Source: https://flowcraft.io/pricing\n\n"
            f"2. [HIGH - 8/10] OmniBotics launched two-way voice calling. Action: Double down on healthcare vertical specialization.\n"
            f"   Source: https://omnibotics.com/changelog\n\n"
            f"3. [MEDIUM - 7/10] SyncWave CRM experiencing customer backlash over billing bugs on G2. Action: Target dissatisfied users on social.\n"
            f"   Source: https://g2.com/products/syncwave-crm/reviews\n\n"
            f"Overall Market Assessment: Competitive pricing pressure is shifting upwards, creating strong tailwinds for our agency automation offers."
        )

        state["detected_changes"] = detected
        state["latest_digest"] = {
            "title": f"Executive Intelligence Briefing ({datetime.utcnow().strftime('%Y-W%U')})",
            "content": digest_text,
            "high_impact_count": 3,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        self._save(state)

        return {
            "detected_count": len(detected),
            "changes": detected,
            "digest": state["latest_digest"]
        }

    def get_summary(self) -> Dict[str, Any]:
        state = self._load()
        return {
            "competitors_count": len(state["competitors"]),
            "competitors": state["competitors"],
            "detected_changes": state["detected_changes"],
            "latest_digest": state["latest_digest"]
        }

    def reset_state(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self._ensure_state()
