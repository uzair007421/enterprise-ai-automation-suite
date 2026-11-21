"""
Project 06: HR AI Recruiter Assistant Router
FastAPI router for demographic PII redaction, blind rubric evaluation, and automated interview scheduling.
"""
import uuid
import time
import json
import datetime
from fastapi import APIRouter, Depends
from core.db import get_db, DatabaseSession
from core.events import event_broker
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
    1. Demographically strips PII (Name, Email, Phone, Pronouns, Grad Year)
    2. Scores strictly against objective 100-point competency rubric
    3. Persists anonymized candidate record into SQLite
    """
    t_start = time.perf_counter()
    session_id = req.session_id or "demo_session"

    event_broker.publish(session_id, {
        "project": "p06_hr",
        "stage": "INGESTION",
        "message": f"Ingesting candidate CV for role '{req.job_role}' ({len(req.raw_cv_text)} characters)..."
    })

    # Step 1: Demographic PII Redaction
    anonymized_text, pii_audit = redact_demographic_pii(req.raw_cv_text)
    event_broker.publish(session_id, {
        "project": "p06_hr",
        "stage": "PII_ANONYMIZATION",
        "redacted_count": pii_audit.redacted_tokens_count,
        "categories": pii_audit.categories_redacted,
        "message": f"Demographic PII stripped: {pii_audit.redacted_tokens_count} tokens redacted ({', '.join(pii_audit.categories_redacted) or 'None'})."
    })

    # Step 2: Competency-Based Rubric Scoring
    rubric, recommendation, strengths, growth_areas, slot = evaluate_candidate_rubric(anonymized_text)
    event_broker.publish(session_id, {
        "project": "p06_hr",
        "stage": "RUBRIC_EVALUATION",
        "score": rubric.total_score,
        "recommendation": recommendation,
        "message": f"Candidate Scored: {rubric.total_score}/100. Recommendation: {recommendation}."
    })

    # Step 3: SQLite Persistence
    candidate_id = f"CAND-{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    db.execute("""
        INSERT INTO p06_candidates (
            id, redacted_cv_text, pii_audit_json, rubric_score,
            score_breakdown_json, recommendation, scheduled_interview_slot, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_id,
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
        anonymized_cv=anonymized_text,
        pii_audit=pii_audit,
        rubric=rubric,
        recommendation=recommendation,
        strengths=strengths,
        growth_areas=growth_areas,
        scheduled_slot=slot,
        execution_time_ms=round(t_elapsed, 2)
    )

@router.get("/candidates")
def get_candidate_registry(db: DatabaseSession = Depends(get_db)):
    """Returns anonymized candidate records and rubric audit history."""
    rows = db.fetchall("SELECT * FROM p06_candidates ORDER BY created_at DESC LIMIT 50")
    return {"candidates": rows, "count": len(rows)}
