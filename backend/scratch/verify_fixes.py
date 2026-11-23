"""Quick logic verification of all 6 fixes — runs without pytest framework."""
import sys
sys.path.insert(0, ".")

from projects.p07_voice.triage_engine import triage_dental_inquiry
from projects.p04_invoice.ocr_engine import parse_text_heuristics
from projects.p10_finance.tools import query_saas_metrics
from projects.p04_invoice.accounting_adapter import AccountingAdapter

failures = []

# ── P07: paraphrased emergency phrases ────────────────────────────────────────
cases = [
    ("i cannot breathe properly",                            True,  "MEDICAL_EMERGENCY"),
    ("bleeding won't stop for an hour",                      True,  "MEDICAL_EMERGENCY"),
    ("I can't swallow and my tongue is swelling up",         True,  "MEDICAL_EMERGENCY"),
    ("mera chehra bohat sooj gaya hai aur bukhar hai",       None,  "URGENT+"),  # URGENT or higher
    ("my gum is bleeding a little when I brush",             False, "ROUTINE_CHECKUP"),
    ("I have a severe toothache with fever",                 False, "URGENT_APPOINTMENT"),
]

print("── P07 Triage ──────────────────────────────────────────────────")
for transcript, expected_emergency, expected_tier in cases:
    r = triage_dental_inquiry(transcript)
    ok = True
    if expected_emergency is not None and r.is_emergency != expected_emergency:
        ok = False
    if expected_tier == "URGENT+":
        if r.urgency_tier not in ("URGENT_APPOINTMENT", "MEDICAL_EMERGENCY", "CRITICAL_EMERGENCY"):
            ok = False
    elif expected_tier and r.urgency_tier != expected_tier:
        ok = False

    status = "✓" if ok else "✗ FAIL"
    print(f"  {status}  [{r.urgency_tier}] emergency={r.is_emergency}  «{transcript[:50]}»")
    if not ok:
        failures.append(f"P07 triage: '{transcript}' → tier={r.urgency_tier} emergency={r.is_emergency}  "
                        f"(expected tier={expected_tier} emergency={expected_emergency})")

# ── P04: invoice number parse ─────────────────────────────────────────────────
print("\n── P04 Invoice Parser ──────────────────────────────────────────")
r1 = parse_text_heuristics("Invoice #: S-1001 from vendor Acme Corp total amount 500.00")
ok = r1.invoice_number == "S-1001"
print(f"  {'✓' if ok else '✗ FAIL'}  invoice_num='{r1.invoice_number}'  (expected S-1001)")
if not ok:
    failures.append(f"P04 invoice_num: got '{r1.invoice_number}' expected 'S-1001'")

r2 = parse_text_heuristics("Vendor: TechSoft Inc Invoice No: INV-9020 Date: 2026-01-15 Total: 1200.00")
vendor_ok = r2.vendor_name and len(r2.vendor_name) < 25  # should not be the entire line
print(f"  {'✓' if vendor_ok else '✗ FAIL'}  vendor='{r2.vendor_name}'  (should be short, not full line)")
if not vendor_ok:
    failures.append(f"P04 vendor parse: got '{r2.vendor_name}' (too long or None)")

# ── P10: ARR/MRR/runway tool ──────────────────────────────────────────────────
print("\n── P10 SaaS Metrics ────────────────────────────────────────────")
m = query_saas_metrics()
ok = m["arr_usd"] > 0 and m["mrr_usd"] > 0 and m["runway_months"] > 0
print(f"  {'✓' if ok else '✗ FAIL'}  ARR=${m['arr_usd']:,.0f}  MRR=${m['mrr_usd']:,.0f}  runway={m['runway_months']}mo")
if not ok:
    failures.append(f"P10 saas_metrics: unexpected zero values {m}")

# P10: agent maps ARR query
from projects.p10_finance.agent import finguard_agent
reasoning, proposal, answer = finguard_agent.process_query(
    "What is our ARR, MRR and runway?", "cfo_user", "cfo"
)
arr_mapped = proposal is not None and proposal.tool_name == "query_saas_metrics"
print(f"  {'✓' if arr_mapped else '✗ FAIL'}  ARR query maps to tool_name={getattr(proposal,'tool_name',None)}")
if not arr_mapped:
    failures.append(f"P10 agent ARR mapping: proposal={proposal}")

# ── P04: accounting adapter QBO_LIVE_MODE ────────────────────────────────────
print("\n── P04 Accounting Adapter ──────────────────────────────────────")
a = AccountingAdapter()
ok = hasattr(a, "live_mode")
print(f"  {'✓' if ok else '✗ FAIL'}  live_mode attr exists = {getattr(a,'live_mode',None)}")
if not ok:
    failures.append("P04 AccountingAdapter missing live_mode attribute")

# ── P04: Optional import (NameError check) ───────────────────────────────────
print("\n── P04 Optional Import ─────────────────────────────────────────")
try:
    from projects.p04_invoice.accounting_adapter import AccountingAdapter as _AA
    print("  ✓  accounting_adapter imported without NameError")
except NameError as e:
    failures.append(f"P04 Optional NameError: {e}")
    print(f"  ✗ FAIL  NameError: {e}")

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
if failures:
    print(f"FAILURES ({len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED ✓")
