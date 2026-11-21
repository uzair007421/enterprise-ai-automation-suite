"""
Simulated CRM System (HubSpot / GoHighLevel / Salesforce compatible schema)
Maintains audit logs, pipeline stages, contact cards, and activity feeds.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

class RealEstateCRM:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "crm_db.json")
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            initial_data = {
                "contacts": {},
                "deals": {},
                "activity_log": [],
                "stats": {
                    "total_leads_received": 0,
                    "qualified_leads": 0,
                    "offers_drafted": 0,
                    "offers_approved": 0,
                    "offers_dispatched": 0
                }
            }
            self._save(initial_data)

    def _load(self) -> Dict[str, Any]:
        with open(self.db_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def log_lead_intake(self, lead_dict: Dict[str, Any]) -> str:
        db = self._load()
        lead_id = lead_dict["lead_id"]
        db["contacts"][lead_id] = {
            "lead_id": lead_id,
            "name": lead_dict["name"],
            "email": lead_dict["email"],
            "phone": lead_dict["phone"],
            "source": lead_dict["source"],
            "stage": "New Lead",
            "created_at": datetime.utcnow().isoformat(),
            "notes": [f"Lead acquired via {lead_dict['source']}. Inquiry: {lead_dict['raw_inquiry']}"]
        }
        db["stats"]["total_leads_received"] += 1
        
        self._log_activity(db, lead_id, "LEAD_INTAKE", f"Lead received from {lead_dict['source']}")
        self._save(db)
        return lead_id

    def update_qualification(self, lead_id: str, qual_report: Dict[str, Any]):
        db = self._load()
        if lead_id in db["contacts"]:
            status = qual_report["qualification_status"]
            db["contacts"][lead_id]["qualification"] = qual_report
            db["contacts"][lead_id]["stage"] = "Qualified Lead" if status in ["HOT", "WARM"] else "Disqualified / Nurture"
            if status in ["HOT", "WARM"]:
                db["stats"]["qualified_leads"] += 1
            self._log_activity(
                db, 
                lead_id, 
                "QUALIFICATION_COMPLETED", 
                f"Agent 1 evaluated lead as {status} (Score: {qual_report['score']}/100). Recommendation: {qual_report['recommended_action']}"
            )
            self._save(db)

    def update_property_matches(self, lead_id: str, matches: List[Dict[str, Any]]):
        db = self._load()
        if lead_id in db["contacts"]:
            db["contacts"][lead_id]["property_matches"] = matches
            db["contacts"][lead_id]["stage"] = "Properties Matched"
            match_titles = ", ".join([f"{m['title']} ({m['match_score']}%)" for m in matches[:2]])
            self._log_activity(
                db,
                lead_id,
                "MATCHES_FOUND",
                f"Agent 2 identified {len(matches)} suitable properties: {match_titles}"
            )
            self._save(db)

    def record_draft_offer(self, lead_id: str, offer_dict: Dict[str, Any]):
        db = self._load()
        if lead_id in db["contacts"]:
            db["deals"][offer_dict["offer_id"]] = {
                "offer_id": offer_dict["offer_id"],
                "lead_id": lead_id,
                "property_id": offer_dict["property_id"],
                "headline": offer_dict["headline"],
                "proposed_price": offer_dict["proposed_price"],
                "incentives": offer_dict["incentive_package"],
                "status": "Pending Human Approval",
                "created_at": datetime.utcnow().isoformat()
            }
            db["contacts"][lead_id]["stage"] = "Offer Drafted (Awaiting Human Approval)"
            db["stats"]["offers_drafted"] += 1
            self._log_activity(
                db,
                lead_id,
                "OFFER_DRAFTED",
                f"Agent 3 created draft offer for {offer_dict['property_id']} at ${offer_dict['proposed_price']:,}. Sent to Broker Review Desk."
            )
            self._save(db)

    def record_human_decision(self, lead_id: str, offer_id: str, decision: str, reviewer: str, comments: str):
        db = self._load()
        if offer_id in db["deals"]:
            db["deals"][offer_id]["status"] = decision
            db["deals"][offer_id]["reviewed_by"] = reviewer
            db["deals"][offer_id]["review_comments"] = comments
            db["deals"][offer_id]["reviewed_at"] = datetime.utcnow().isoformat()

        if lead_id in db["contacts"]:
            if decision == "APPROVED":
                db["contacts"][lead_id]["stage"] = "Offer Approved & Ready to Dispatch"
                db["stats"]["offers_approved"] += 1
            else:
                db["contacts"][lead_id]["stage"] = f"Offer {decision}"

            self._log_activity(
                db,
                lead_id,
                f"HUMAN_REVIEW_{decision}",
                f"Licensed broker {reviewer} marked offer as {decision}. Notes: {comments}"
            )
            self._save(db)

    def record_dispatch(self, lead_id: str, channel: str):
        db = self._load()
        if lead_id in db["contacts"]:
            db["contacts"][lead_id]["stage"] = "Offer Sent to Buyer"
            db["stats"]["offers_dispatched"] += 1
            self._log_activity(
                db,
                lead_id,
                "OFFER_DISPATCHED",
                f"Offer package dispatched successfully via {channel} to {db['contacts'][lead_id]['email']}"
            )
            self._save(db)

    def _log_activity(self, db: Dict[str, Any], lead_id: str, action: str, details: str):
        db["activity_log"].insert(0, {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "lead_id": lead_id,
            "action": action,
            "details": details
        })

    def get_full_state(self) -> Dict[str, Any]:
        return self._load()
