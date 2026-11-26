"""
Project 06: HR AI Recruiter Assistant Router
FastAPI router for demographic PII redaction, blind rubric evaluation, and automated interview scheduling.
SaaS Multi-Tenant Partitioning and Strict Merit-Based Governance.
"""
import uuid
import time
import json
import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from core.db import get_db, DatabaseSession
from core.events import event_broker
from core.security import verify_admin_token, mask_email, mask_phone
from .schemas import (
    CandidateScreenRequest,
    CandidateScreenResponse
)
from .pii_redactor import redact_demographic_pii
from .rubric_evaluator import evaluate_candidate_rubric

router = APIRouter(prefix="/api/ai/hr-recruiter", tags=["P06 HR Recruiter Assistant"])

@router.post("/screen", response_model=CandidateScreenResponse)
def screen_candidate(req: CandidateScreenRequest, db: DatabaseSession = Depends(get_db)):
    """
    Executes blind candidate evaluation:
    1. Demographically strips PII (Name, Email, Phone, Pronouns, Grad Year, Religion, Family, University)
    2. Scores strictly against objective 100-point competency rubric
    3. Persists anonymized candidate record into database partitioned by tenant_id
    """
    t_start = time.perf_counter()
    session_id = req.session_id or "demo_session"
    tenant_id = req.tenant_id or "default_company"

    event_broker.publish(session_id, {
        "project": "p06_hr",
        "stage": "INGESTION",
        "message": f"Ingesting candidate CV for role '{req.job_role}' under organization [{tenant_id}] ({len(req.raw_cv_text)} characters)..."
    })

    # Step 1: Demographic PII & Bias Redaction + Mandatory Fail-Closed Residual Check
    anonymized_text, pii_audit = redact_demographic_pii(req.raw_cv_text)
    event_broker.publish(session_id, {
        "project": "p06_hr",
        "stage": "PII_ANONYMIZATION",
        "redacted_count": pii_audit.redacted_tokens_count,
        "categories": pii_audit.categories_redacted,
        "is_fully_anonymized": pii_audit.is_fully_anonymized,
        "residual_categories": pii_audit.residual_categories,
        "message": f"Demographic PII stripped: {pii_audit.redacted_tokens_count} tokens redacted ({', '.join(pii_audit.categories_redacted) or 'None'})."
    })

    if not pii_audit.is_fully_anonymized:
        return JSONResponse(
            status_code=422,
            content={
                "status": "REDACTION_INCOMPLETE",
                "residual_categories": pii_audit.residual_categories,
            },
        )

    # Step 2: Competency-Based Rubric Scoring
    rubric, recommendation, strengths, growth_areas, slot = evaluate_candidate_rubric(anonymized_text, job_role=req.job_role)
    event_broker.publish(session_id, {
        "project": "p06_hr",
        "stage": "RUBRIC_EVALUATION",
        "score": rubric.total_score,
        "recommendation": recommendation,
        "message": f"Candidate Scored: {rubric.total_score}/100. Recommendation: {recommendation}."
    })

    # Step 3: Database Persistence with Multi-Tenant Partitioning
    candidate_id = f"CAND-{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    db.execute("""
        INSERT INTO p06_candidates (
            id, tenant_id, redacted_cv_text, pii_audit_json, rubric_score,
            score_breakdown_json, recommendation, scheduled_interview_slot, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_id,
        tenant_id,
        anonymized_text,
        json.dumps(pii_audit.model_dump()),
        rubric.total_score,
        json.dumps(rubric.model_dump()),
        recommendation,
        slot or "N/A",
        now_str
    ))
    db.commit()

    t_elapsed = (time.perf_counter() - t_start) * 1000.0

    return CandidateScreenResponse(
        candidate_id=candidate_id,
        tenant_id=tenant_id,
        engine="rules",
        anonymized_cv=anonymized_text,
        pii_audit=pii_audit,
        rubric=rubric,
        recommendation=recommendation,
        strengths=strengths,
        growth_areas=growth_areas,
        scheduled_slot=slot,
        execution_time_ms=round(t_elapsed, 2)
    )

@router.get("/candidates", dependencies=[Depends(verify_admin_token)])
def get_candidate_registry(
    tenant_id: Optional[str] = Query(default=None, description="Filter candidates by organization tenant partition"),
    db: DatabaseSession = Depends(get_db)
):
    """Returns anonymized candidate records and rubric audit history filtered by tenant."""
    if tenant_id:
        rows = db.fetchall("SELECT * FROM p06_candidates WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 50", (tenant_id,))
    else:
        rows = db.fetchall("SELECT * FROM p06_candidates ORDER BY created_at DESC LIMIT 50")

    candidates = []
    for r in rows:
        d = dict(r)
        if "email" in d:
            d["email"] = mask_email(d["email"])
        if "phone" in d:
            d["phone"] = mask_phone(d["phone"])
        candidates.append(d)
    return {"candidates": candidates, "count": len(candidates), "tenant_id": tenant_id}
