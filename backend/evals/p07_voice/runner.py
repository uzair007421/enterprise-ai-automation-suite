"""
Evaluation Harness for Project 07: Dental Appointment Intake Prototype (Non-Diagnostic)
Measures keyword-routing accuracy on a mixed benchmark of standard & unseen paraphrased transcripts.
NOTE: This is a rule-based booking prototype, NOT a clinical medical triage tool.
"""
import json
import time
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from projects.p07_voice.triage_engine import triage_dental_inquiry

def run_eval():
    cases_file = os.path.join(current_dir, "cases.jsonl")
    results_file = os.path.join(current_dir, "results.json")
    report_file = os.path.join(current_dir, "report.md")

    cases = []
    with open(cases_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    total = len(cases)
    total_emergencies = sum(1 for c in cases if c["is_emergency"])
    detected_emergencies = 0
    tier_matches = 0
    latencies = []

    for c in cases:
        t0 = time.perf_counter()
        res = triage_dental_inquiry(c["transcript"])
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        if c["is_emergency"] and res.is_emergency:
            detected_emergencies += 1

        tier_match = (
            res.urgency_tier == c["expected_tier"] or
            (c["expected_tier"] == "URGENT" and res.urgency_tier in ("URGENT", "URGENT_APPOINTMENT")) or
            (c["expected_tier"] == "URGENT_APPOINTMENT" and (res.urgency_tier in ("URGENT", "URGENT_APPOINTMENT") or res.intent == "URGENT_APPOINTMENT"))
        )
        if tier_match:
            tier_matches += 1

    emergency_recall = round((detected_emergencies / total_emergencies * 100.0), 2)
    tier_accuracy = round((tier_matches / total * 100.0), 2)
    avg_latency = round(sum(latencies) / len(latencies), 3)

    results = {
        "benchmark": "P07 Dental Intake Keyword Routing Evaluation (Non-Diagnostic Demo)",
        "total_cases": total,
        "total_critical_emergencies": total_emergencies,
        "emergency_recall_pct": emergency_recall,
        "tier_classification_accuracy_pct": tier_accuracy,
        "average_triage_latency_ms": avg_latency,
        "status": "PASSED" if emergency_recall >= 85.0 and tier_accuracy >= 80.0 else "NEEDS_IMPROVEMENT"
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    report_md = f"""# Project 07: Dental Intake & Booking Prototype - Evaluation Report

- **Date**: 2026-11-25
- **Disclaimer**: Rule-based scheduling prototype — **NOT a clinical or medical triage device**.
- **Evaluation Dataset**: {total} Transcripts (Standard + Unseen Natural-Language Paraphrases)
- **Status**: **{results['status']}**

## Measured Prototype Metrics

| Metric | Measured | Notes |
|---|---|---|
| Emergency Keyword Recall | **{emergency_recall}%** | Includes unseen natural-language paraphrases |
| Tier Classification Accuracy | **{tier_accuracy}%** | |
| Average Routing Latency | **{avg_latency} ms** | |
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_eval()
