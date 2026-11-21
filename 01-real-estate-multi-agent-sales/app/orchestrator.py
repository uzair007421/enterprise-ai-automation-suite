"""
Multi-Agent Orchestrator & Human-in-the-Loop Controller
Coordinates Lead Qualifier -> Property Matcher -> Offer Drafter -> Human Approval Queue -> CRM Sync
"""
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .models import Lead, WorkflowState, QualificationReport, PropertyMatch, DraftOffer
from .agents import LeadQualifierAgent, PropertyMatcherAgent, OfferDrafterAgent
from .crm import RealEstateCRM

class RealEstateMultiAgentOrchestrator:
    def __init__(self, crm: Optional[RealEstateCRM] = None):
        self.crm = crm or RealEstateCRM()
        self.qualifier = LeadQualifierAgent()
        self.matcher = PropertyMatcherAgent()
        self.drafter = OfferDrafterAgent()
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.approval_queue: List[str] = []  # List of lead_ids pending review

    def ingest_lead(self, lead_data: Dict[str, Any]) -> WorkflowState:
        """Step 1: Intake lead and log to CRM."""
        lead = Lead(**lead_data)
        state = WorkflowState(lead_id=lead.lead_id, lead=lead, status="INTAKE")
        self.active_workflows[lead.lead_id] = state
        self.crm.log_lead_intake(lead.to_dict())
        return state

    def run_agent_pipeline(self, lead_id: str) -> WorkflowState:
        """Runs Agent 1, Agent 2, and Agent 3 sequentially."""
        if lead_id not in self.active_workflows:
            raise ValueError(f"Lead ID {lead_id} not found in pipeline.")

        state = self.active_workflows[lead_id]
        lead = state.lead

        # Step 2: Agent 1 (Qualify)
        qual_report = self.qualifier.process(lead)
        state.qualification = qual_report
        state.status = "QUALIFIED"
        self.crm.update_qualification(lead_id, qual_report.to_dict())

        # If lead is disqualified, stop early
        if qual_report.qualification_status == "DISQUALIFIED":
            state.status = "DISQUALIFIED"
            state.updated_at = datetime.utcnow().isoformat()
            return state

        # Step 3: Agent 2 (Match Property)
        matches = self.matcher.process(lead, qual_report)
        state.matched_properties = matches
        state.status = "MATCHED"
        self.crm.update_property_matches(lead_id, [m.to_dict() for m in matches])

        if not matches:
            state.status = "NO_MATCH"
            state.updated_at = datetime.utcnow().isoformat()
            return state

        # Step 4: Agent 3 (Draft Offer)
        top_match = matches[0]
        offer = self.drafter.process(lead, qual_report, top_match)
        state.draft_offer = offer
        state.status = "PENDING_HUMAN_APPROVAL"
        state.updated_at = datetime.utcnow().isoformat()
        
        self.crm.record_draft_offer(lead_id, offer.to_dict())
        if lead_id not in self.approval_queue:
            self.approval_queue.append(lead_id)

        return state

    def human_review_action(
        self,
        lead_id: str,
        decision: str,  # "APPROVED", "REJECTED", "MODIFIED"
        reviewer: str,
        comments: str,
        modified_price: Optional[float] = None,
        modified_letter: Optional[str] = None
    ) -> WorkflowState:
        """Step 5: Licensed broker human-in-the-loop sign-off."""
        if lead_id not in self.active_workflows:
            raise ValueError(f"Lead {lead_id} not found.")

        state = self.active_workflows[lead_id]
        if not state.draft_offer:
            raise ValueError("No draft offer exists to review.")

        if modified_price is not None:
            state.draft_offer.proposed_price = modified_price
        if modified_letter is not None:
            state.draft_offer.formal_offer_letter = modified_letter

        state.human_feedback = comments
        state.human_reviewer = reviewer
        state.status = decision
        state.updated_at = datetime.utcnow().isoformat()

        if lead_id in self.approval_queue:
            self.approval_queue.remove(lead_id)

        self.crm.record_human_decision(
            lead_id=lead_id,
            offer_id=state.draft_offer.offer_id,
            decision=decision,
            reviewer=reviewer,
            comments=comments
        )

        # Step 6: Dispatch if approved
        if decision == "APPROVED":
            dispatch_channel = "WhatsApp & Email" if "WhatsApp" in state.lead.source else "Email"
            self.crm.record_dispatch(lead_id, dispatch_channel)
            state.status = "DISPATCHED"

        return state

    def get_dashboard_summary(self) -> Dict[str, Any]:
        crm_data = self.crm.get_full_state()
        return {
            "crm_stats": crm_data["stats"],
            "recent_activity": crm_data["activity_log"][:10],
            "pending_approvals_count": len(self.approval_queue),
            "workflows": {lid: s.to_dict() for lid, s in self.active_workflows.items()}
        }
