"""
Unit & Integration Tests for Project 06: HR AI Recruiter Assistant
Verifies:
1. Demographic PII Redaction (stripping names, emails, phones, grad years).
2. Competency Rubric Scoring (Technical, Architecture, Impact).
3. Recommendation Gate (ADVANCE_TO_INTERVIEW vs HOLD vs REJECT).
4. SQLite persistence of anonymized candidate audit record.
"""
import pytest
from core.db import init_db, DatabaseSession
from projects.p06_hr.pii_redactor import redact_demographic_pii
from projects.p06_hr.rubric_evaluator import evaluate_candidate_rubric
from projects.p06_hr.router import screen_candidate
from projects.p06_hr.schemas import CandidateScreenRequest

def setup_module(module):
    init_db()

def test_demographic_pii_redaction():
    cv = """Johnathan Smith
Email: john.smith@university.edu
Phone: (415) 555-8123
Graduated in 2016 from Stanford University.
He is a senior engineer with Python and Docker expertise."""
    anonymized, audit = redact_demographic_pii(cv)
    assert "[REDACTED_EMAIL]" in anonymized
    assert "[REDACTED_PHONE]" in anonymized
    assert "[CANDIDATE_ANONYMOUS_PROFILE]" in anonymized
    assert "john.smith@university.edu" not in anonymized
    assert "(415) 555-8123" not in anonymized
    assert audit.redacted_tokens_count >= 3
    assert audit.is_fully_anonymized is True

def test_strong_candidate_rubric():
    strong_cv = """[CANDIDATE_ANONYMOUS_PROFILE]
Principal Full-Stack & AI Systems Architect.
Extensive experience with Python, FastAPI, TypeScript, React, Docker, PostgreSQL, LLM embeddings, and vector databases.
Designed distributed microservices architecture on AWS with Redis caching and event-driven SSE telemetry.
Accomplishments:
- Reduced latency by 45% across core APIs.
- Scaled to 2m users and supported 50k requests per minute.
- Saved $150k annually in cloud infrastructure expenditures."""
    rubric, rec, strengths, growth, slot = evaluate_candidate_rubric(strong_cv)
    assert rubric.total_score >= 75
    assert rec == "ADVANCE_TO_INTERVIEW"
    assert slot is not None
    assert len(strengths) >= 2

def test_weak_candidate_rubric():
    weak_cv = """[CANDIDATE_ANONYMOUS_PROFILE]
Junior assistant with some basic computer skills.
Did office filing and answered basic emails. No programming or cloud experience."""
    rubric, rec, strengths, growth, slot = evaluate_candidate_rubric(weak_cv)
    assert rubric.total_score < 55
    assert rec == "REJECT"
    assert slot is None

def test_end_to_end_screen_and_db_persistence():
    session = DatabaseSession()
    req = CandidateScreenRequest(
        raw_cv_text="""Sarah Jenkins
sarah.jenkins@techcorp.io | (206) 555-0199
Class of 2018 MIT.
Senior Python Backend Engineer. Built microservices with FastAPI, Docker, and PostgreSQL.
Scaled to 500k users and reduced query response times by 35%.""",
        job_role="Senior Backend Engineer",
        session_id="test_hr_session"
    )

    res = screen_candidate(req, db=session)
    assert res.pii_audit.is_fully_anonymized is True
    assert "sarah.jenkins@techcorp.io" not in res.anonymized_cv
    assert res.recommendation in ("ADVANCE_TO_INTERVIEW", "HOLD_FOR_REVIEW")

    # Verify SQLite row
    row = session.query_one("SELECT * FROM p06_candidates WHERE id = ?", (res.candidate_id,))
    assert row is not None
    assert "[REDACTED_EMAIL]" in row["redacted_cv_text"]
    assert row["rubric_score"] == res.rubric.total_score

    session.close()
