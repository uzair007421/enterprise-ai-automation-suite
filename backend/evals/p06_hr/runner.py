"""
Evaluation Harness for Project 06: HR AI Recruiter Assistant
Measures honestly:
1. PII Redaction & Fail-Closed Gate across benchmark + diverse unseen synthetic CVs.
2. Per-category leakage check (DOB, nationality, religion/sect, family, URLs, years).
3. Competency Rubric Recommendation Accuracy.
"""
import json
import re
import time
import os
import sys
import random

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from core.db import init_db, DatabaseSession
from projects.p06_hr.pii_redactor import redact_demographic_pii
from projects.p06_hr.rubric_evaluator import evaluate_candidate_rubric
from projects.p06_hr.schemas import CandidateScreenRequest


def run_eval():
    init_db()
    cases_file = os.path.join(current_dir, "cases.jsonl")
    results_file = os.path.join(current_dir, "results.json")

    cases = []
    with open(cases_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    total = len(cases)
    pii_redacted_cleanly = 0
    recommendation_matches = 0
    mismatch_contained = 0
    mismatch_total = 0
    latencies = []

    for c in cases:
        role = c.get("job_role", "Senior Full-Stack / AI Engineer")
        t0 = time.perf_counter()
        redacted, audit = redact_demographic_pii(c["cv"])
        rubric, rec, _, _, _ = evaluate_candidate_rubric(redacted, job_role=role)
        latencies.append((time.perf_counter() - t0) * 1000.0)

        name_clean = c["name"].lower() not in redacted.lower()
        email_clean = "@" not in redacted and "[at]" not in redacted.lower()
        phone_clean = (c["phone"] not in redacted) if c.get("phone") else True
        if name_clean and email_clean and phone_clean and audit.is_fully_anonymized:
            pii_redacted_cleanly += 1

        if rec == c["expected_rec"]:
            recommendation_matches += 1
        if c.get("max_score"):
            mismatch_total += 1
            if rubric.total_score <= c["max_score"]:
                mismatch_contained += 1

    # Diverse unseen synthetic category benchmark (per-category honesty)
    rng = random.Random(99)
    synth_specs = [
        ("dob_age", ["DOB 14/05/1990", "Born 1988", "aged 34", "Date of Birth: 1992-07-11"]),
        ("phones_unformatted", ["+923155551234", "03155551234", "+92 3155551234"]),
        ("locations_regional", ["Sialkot, Sindh", "Gujranwala", "Bahawalpur", "Hyderabad"]),
        ("nationality", ["Pakistani national", "Indian citizen", "German national"]),
        ("religion_sect", ["Sunni", "Shia", "Catholic", "Sikh", "Ahmadi"]),
        ("family", ["wife", "husband", "partner", "stepdaughter", "engaged", "divorced"]),
        ("urls_handles", ["https://linkedin.com/in/zainraza", "behance.net/sanaali", "dribbble.com/omarkhan", "@omarkhan"]),
        ("years", ["MBA 2003", "B.Sc. 2015", "Class of 2018"]),
    ]
    cat_stats = {}
    for cat_key, samples in synth_specs:
        passed = 0
        for idx, marker in enumerate(samples):
            cv = f"Candidate Name: Test User{idx}\n{marker}\nPython FastAPI engineer with 5 years of experience."
            redacted, audit = redact_demographic_pii(cv)
            tok = marker.replace(",", " ").split()[-1].lower()
            if tok.isalpha():
                cleaned = not re.search(rf"\b{re.escape(tok)}\b", redacted.lower())
            else:
                cleaned = tok not in redacted.lower()
            if cleaned or not audit.is_fully_anonymized:
                passed += 1
        cat_stats[cat_key] = {"passed": passed, "total": len(samples), "pct": round(passed / len(samples) * 100.0, 2)}

    anonymization_rate = round((pii_redacted_cleanly / total * 100.0), 2)
    recommendation_accuracy = round((recommendation_matches / total * 100.0), 2)
    avg_latency_ms = round((sum(latencies) / len(latencies)), 2) if latencies else 0.0

    results = {
        "project": "06-hr-ai-recruiter-assistant",
        "benchmark_name": "Candidate PII Category Redaction & Fail-Closed Eval",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ"),
        "total_candidates_screened": total,
        "pii_anonymization_success_percent": anonymization_rate,
        "synthetic_category_protection": cat_stats,
        "recommendation_accuracy_percent": recommendation_accuracy,
        "role_mismatch_containment_percent": 100.0 if mismatch_total == 0 else round((mismatch_contained / mismatch_total * 100.0), 2),
        "average_screening_latency_ms": avg_latency_ms,
        "engine": "rules",
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    run_eval()
