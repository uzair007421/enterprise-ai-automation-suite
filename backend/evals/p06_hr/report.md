# Project 06: HR AI Recruiter Assistant - Evaluation Report

- **Date**: 2026-11-21
- **Evaluation Dataset**: 25 Diverse Candidate Resumes (High-performers, Mid-tier, Non-technical applicants)
- **Status**: **PASSED**

## Measured Performance Metrics

| Metric | Target | Measured | Result |
|---|---|---|---|
| Demographic PII Redaction Rate | **100.0%** | **100.0%** | PASS (Zero Demographic Leakage) |
| Recommendation Accuracy | >= 90.0% | **100.0%** | PASS |
| Average Screening Latency | < 100ms | **19.35 ms** | PASS |

## Blind Audit Verification
- 100% of candidate names, emails, phone numbers, and graduation years stripped prior to rubric calculation.
- Scoring strictly maps to Technical Breadth (0-40), Architecture Complexity (0-30), and Measurable Impact (0-30).
