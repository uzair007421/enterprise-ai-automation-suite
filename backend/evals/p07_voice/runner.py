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
from tests.test_p07_voice import HOLDOUT_EMERGENCIES, HOLDOUT_NON_EMERGENCIES


def _eval_split(items):
    total = len(items)
    em_total = sum(1 for c in items if c["is_emergency"])
    non_em_total = total - em_total
    em_hits = 0
    false_alarms = 0
    tier_matches = 0
    latencies = []
    for c in items:
        t0 = time.perf_counter()
        res = triage_dental_inquiry(c["transcript"])
        latencies.append((time.perf_counter() - t0) * 1000.0)
        if c["is_emergency"] and res.is_emergency:
            em_hits += 1
        elif (not c["is_emergency"]) and res.is_emergency:
            false_alarms += 1
        exp = c.get("expected_tier")
        if exp and (res.urgency_tier == exp or (exp in ("URGENT", "URGENT_APPOINTMENT") and res.urgency_tier == "URGENT_APPOINTMENT")):
            tier_matches += 1
    return {
        "cases": total,
        "emergency_recall_pct": round((em_hits / em_total * 100.0), 2) if em_total else 0.0,
        "false_alarm_count": false_alarms,
        "non_emergency_total": non_em_total,
        "tier_accuracy_pct": round((tier_matches / total * 100.0), 2) if total else 0.0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
    }


def run_eval():
    cases_file = os.path.join(current_dir, "cases.jsonl")
    results_file = os.path.join(current_dir, "results.json")
    report_file = os.path.join(current_dir, "report.md")

    dev_cases = []
    with open(cases_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                dev_cases.append(json.loads(line))

    holdout_cases = (
        [{"transcript": t, "is_emergency": True, "expected_tier": "CRITICAL_EMERGENCY"} for t in HOLDOUT_EMERGENCIES]
        + [{"transcript": t, "is_emergency": False, "expected_tier": "ROUTINE_CHECKUP"} for t in HOLDOUT_NON_EMERGENCIES]
    )

    dev_metrics = _eval_split(dev_cases)
    holdout_metrics = _eval_split(holdout_cases)

    results = {
        "benchmark": "P07 Dental Intake Concept-Group Evaluation (Non-Diagnostic Demo)",
        "train_dev": dev_metrics,
        "holdout": holdout_metrics,
        "status": "PASSED" if holdout_metrics["emergency_recall_pct"] >= 85.0 and holdout_metrics["false_alarm_count"] <= 2 else "NEEDS_IMPROVEMENT",
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    report_md = f"""# Project 07: Dental Appointment Intake Prototype - Evaluation Report

- **Disclaimer**: Rule-based scheduling prototype — **NOT a clinical or medical triage tool**.
- **Status**: **{results['status']}**

## Split Results (Train/Dev vs. Hold-Out)

| Split | Cases | Emergency Recall | False Alarms |
|---|---:|---:|---:|
| Train / Dev | {dev_metrics['cases']} | **{dev_metrics['emergency_recall_pct']}%** | {dev_metrics['false_alarm_count']}/{dev_metrics['non_emergency_total']} |
| Hold-Out (Unseen) | {holdout_metrics['cases']} | **{holdout_metrics['emergency_recall_pct']}%** | {holdout_metrics['false_alarm_count']}/{holdout_metrics['non_emergency_total']} |
"""
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    run_eval()
