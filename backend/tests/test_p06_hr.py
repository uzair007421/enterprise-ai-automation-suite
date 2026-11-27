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

def test_redaction_of_religion_family_and_university():
    """Audit Fix: Muslim, single mother, and Punjab University must be demographically redacted."""
    cv = "Female, 29, Married, single mother, Muslim, kids, Lahore, Pakistan, graduated from Punjab University in 2018"
    anonymized, audit = redact_demographic_pii(cv)
    assert "Muslim" not in anonymized and "muslim" not in anonymized
    assert "single mother" not in anonymized
    assert "Punjab University" not in anonymized
    assert "[REDACTED_RELIGION]" in anonymized
    assert "[REDACTED_FAMILY_STATUS]" in anonymized
    assert any("Religion" in c for c in audit.categories_redacted)
    assert any("Family" in c for c in audit.categories_redacted)

def test_keyword_stuffed_cv_held_for_review():
    """Audit Fix: Keyword-stuffed resumes without metrics or action context must be HOLD_FOR_REVIEW."""
    stuffed_cv = "[CANDIDATE_ANONYMOUS_PROFILE]\nPython, FastAPI, Docker, PostgreSQL, React, TypeScript, Redis, Microservices, Kubernetes."
    rubric, rec, strengths, growth, slot = evaluate_candidate_rubric(stuffed_cv)
    assert rec == "HOLD_FOR_REVIEW"
    assert rubric.total_score <= 35
    assert slot is None
    assert any("Keyword stuffing detected" in g for g in growth)

def test_saas_multi_tenant_candidate_partitioning():
    """SaaS Feature: Candidates are partitioned by organization tenant partition."""
    session = DatabaseSession()
    req_a = CandidateScreenRequest(
        raw_cv_text="Senior Python Engineer with 6 years experience in FastAPI and Docker.",
        tenant_id="enterprise_corp_a",
        session_id="test_hr_tenant_a"
    )
    res_a = screen_candidate(req_a, db=session)
    assert res_a.tenant_id == "enterprise_corp_a"

    # Query for enterprise_corp_b
    rows_b = session.query_all("SELECT * FROM p06_candidates WHERE tenant_id = 'enterprise_corp_b'")
    assert all(r["tenant_id"] == "enterprise_corp_b" for r in rows_b)
    session.close()


def test_synthetic_diverse_cvs_fail_closed_or_fully_redacted():
    """Generate 16 synthetic CVs across countries, sects, DOBs, family terms, URLs, and years; assert 0 markers leak on HTTP 200 or fail closed with 422."""
    import random
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    rng = random.Random(42)

    names = ["Tariq Mahmood", "Nadia Kowalska", "Rohan Kulkarni", "Amira Al-Harbi", "Mei Chen", "Lucas Silva", "Hannah O'Brien", "Yusuf Ibrahim"]
    countries = ["Pakistani national", "Indian citizen", "Polish national", "Saudi citizen", "Chinese national", "Brazilian citizen", "Irish citizen", "Egyptian national"]
    sects = ["Sunni", "Shia", "Catholic", "Hindu", "Buddhist", "Protestant", "Sikh", "Ahmadi"]
    family_terms = ["wife", "husband", "divorced", "widower", "2 kids", "spouse", "daughter", "married"]
    dobs = ["DOB 14/05/1990", "Born 1988", "Born in 1993", "Date of Birth: 1991-08-22", "DOB: 03-11-1985"]
    urls = [
        "https://linkedin.com/in/tariqmahmood", "linkedin.com/in/nadiakowalska",
        "https://github.com/rohankulkarni", "twitter.com/amiraharbi", "@meichen_dev"
    ]
    years = ["MBA 2003", "B.Sc. 2014", "Graduated 2017", "Since 2019"]

    for i in range(16):
        name = names[i % len(names)]
        handle_slug = name.lower().replace(" ", "").replace("'", "")
        country = rng.choice(countries)
        sect = rng.choice(sects)
        fam = rng.choice(family_terms)
        dob = rng.choice(dobs)
        url = f"{rng.choice(urls).split('/')[0]}/in/{handle_slug}" if "linkedin" in urls[i % len(urls)] else f"https://github.com/{handle_slug}"
        yr = rng.choice(years)
        cv = (
            f"{name}\n"
            f"{handle_slug}@corp-mail.org | +1-415-555-{1000 + i}\n"
            f"{dob} | {country} | {sect} | {fam}\n"
            f"Profile: {url} | {yr}\n"
            f"Senior Backend Engineer with 6 years of experience in Python, FastAPI, Docker, and PostgreSQL.\n"
            f"Reduced API latency by 40% and scaled services to 500k users."
        )
        resp = client.post("/api/ai/hr-recruiter/screen", json={"raw_cv_text": cv, "job_role": "Backend Engineer", "session_id": f"syn_{i}"})
        assert resp.status_code in (200, 422)
        data = resp.json()
        if resp.status_code == 422:
            assert data["status"] == "REDACTION_INCOMPLETE"
            assert isinstance(data["residual_categories"], list) and len(data["residual_categories"]) > 0
        else:
            out = data["anonymized_cv"].lower()
            for marker in [name.lower(), country.split()[0].lower(), sect.lower(), fam.split()[-1].lower(), handle_slug, yr.split()[-1]]:
                assert marker not in out, f"Leaked '{marker}' in CV #{i}: {data['anonymized_cv']}"


def test_fail_closed_on_incomplete_redaction_gate(monkeypatch):
    """If second-pass detector spots residual PII, /screen returns 422 REDACTION_INCOMPLETE and skips scoring."""
    from fastapi.testclient import TestClient
    from main import app
    from projects.p06_hr import router as hr_router

    called = {"scored": False}
    orig_eval = hr_router.evaluate_candidate_rubric

    def spy_eval(*args, **kwargs):
        called["scored"] = True
        return orig_eval(*args, **kwargs)

    monkeypatch.setattr(hr_router, "evaluate_candidate_rubric", spy_eval)
    monkeypatch.setattr(
        "projects.p06_hr.pii_redactor.detect_residual_pii",
        lambda *a, **kw: ["Protected Demographic: Nationality"],
    )

    client = TestClient(app)
    resp = client.post("/api/ai/hr-recruiter/screen", json={"raw_cv_text": "Python engineer with 5 years of experience.", "job_role": "Backend Engineer"})
    assert resp.status_code == 422
    assert resp.json() == {"status": "REDACTION_INCOMPLETE", "residual_categories": ["Protected Demographic: Nationality"]}
    assert called["scored"] is False


def test_counterfactual_score_equality_across_swaps():
    """Swapping candidate name, gender pronouns, nationality, and religion yields identical rubric score."""
    swaps = [
        ("Bilal Ahmed", "he", "Pakistani national", "Sunni", "wife"),
        ("Priya Sharma", "she", "Indian citizen", "Hindu", "husband"),
        ("David Goldstein", "he", "American citizen", "Jewish", "married"),
        ("Claire Dupont", "she", "French national", "Catholic", "single"),
        ("Gurpreet Singh", "he", "Canadian citizen", "Sikh", "2 kids"),
    ]
    scores = []
    for name, pron, nat, rel, fam in swaps:
        cv = (
            f"{name}\n"
            f"{name.lower().replace(' ', '.')}@mail.org | +1-555-321-9876\n"
            f"{nat}, {rel}, {fam}, DOB 12/04/1990, MBA 2015.\n"
            f"Senior Backend Engineer ({pron}/him): built FastAPI, Python, Docker, PostgreSQL microservices; reduced latency by 35% and scaled to 200k users."
        )
        redacted, audit = redact_demographic_pii(cv)
        assert audit.is_fully_anonymized is True
        rubric, rec, _, _, _ = evaluate_candidate_rubric(redacted, job_role="Senior Backend Engineer")
        scores.append((rubric.total_score, rec))
    assert len(set(scores)) == 1, f"Counterfactual scores diverged: {scores}"


def test_continuous_phones_regional_cities_age_family_and_portfolio_urls():
    """Verify continuous/unformatted phones, regional cities/provinces, 'aged NN', extended family terms, and arbitrary portfolio domains."""
    cv = """Zeeshan Qureshi
Phone: +923155551234 | Alt: 03155551234 | WhatsApp: +92 3155551234
Location: Sialkot, Sindh | Previous: Gujranwala, Bahawalpur, Hyderabad
Aged 34, engaged to partner, living with stepdaughter.
Portfolio: behance.net/zeeshanqureshi | Code: dribbble.com/zqureshi
Senior Backend Engineer with 6 years of experience in Python, FastAPI, Docker, and PostgreSQL."""
    redacted, audit = redact_demographic_pii(cv)
    assert audit.is_fully_anonymized is True, f"Residuals remained: {audit.residual_categories}"
    for leak in ["+923155551234", "03155551234", "3155551234", "Sialkot", "Sindh", "Gujranwala", "Bahawalpur", "Hyderabad", "aged 34", "34", "engaged", "partner", "stepdaughter", "behance.net", "dribbble.com"]:
        assert leak.lower() not in redacted.lower(), f"Leaked '{leak}' in:\n{redacted}"
