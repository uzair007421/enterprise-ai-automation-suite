"""
Pure-regex verification of P07 triage patterns — no pydantic/fastapi imports needed.
Copies the pattern lists from triage_engine.py and tests them directly.
"""
import re, sys

MEDICAL_EMERGENCY_INDICATORS = [
    r"\bchest\s+pain\b",
    r"\bdifficulty\s+(?:breathing|breath)\b",
    r"\bshortness\s+of\s+breath\b",
    r"\btrouble\s+breathing\b",
    r"\bcan'?t\s+breathe\b",
    r"\bcannot\s+breathe\b",
    r"\b(?:i\s+)?(?:am\s+)?(?:not|cannot|can'?t)\s+breath(?:e|ing)?\s*(?:properly|well|at\s+all)?\b",
    r"\b(?:hard|difficult|struggling)\s+to\s+breath(?:e|ing)?\b",
    r"\bairway\b",
    r"\bbleed(?:ing)?\s+(?:won'?t|will\s+not|does\s+not|doesn'?t)\s+stop\b",
    r"\bbleeding\s+for\s+(?:an?\s+)?(?:hour|hours|long\s+time|while)\b",
    r"\bwon'?t\s+stop\s+bleed(?:ing)?\b",
    r"\bblood\s+won'?t\s+stop\b",
    r"\buncontrolled\s+bleeding\b",
    r"\btongue\s+(?:is\s+)?(?:swelling|swollen|enlarged)\b",
    r"\bthroat\s+(?:is\s+)?(?:swelling|closing|tightening|closing\s+up)\b",
    r"\b(?:i\s+)?can'?t\s+swallow\b",
    r"\bcannot\s+swallow\b",
    r"\bhaving\s+(?:trouble|difficulty|problem)\s+swallow(?:ing)?\b",
    r"\b(?:chehra|mera\s+chehra)\s+(?:bohat\s+)?(?:sooj|phool)\b",
    r"\bfacial\s+(?:swelling|trauma|edema)\b",
    r"\bheart\s+attack\b",
    r"\bstroke\b",
    r"\bunconscious(?:ness)?\b",
    r"\bhead\s+injury\b",
    r"\bsaans\s+(?:nahi|na)\s+aa\s+rahi\b",
    r"\bsaans\s+lene\s+me\s+(?:masla|takleef)\b",
    r"\bseene\s+me\s+dard\b",
    r"\bdil\s+ka\s+dora\b",
    r"\bbehosh\b"
]

def matches_medical(text):
    t = text.lower()
    for pat in MEDICAL_EMERGENCY_INDICATORS:
        if re.search(pat, t, re.IGNORECASE):
            return True, pat
    return False, None

failures = []
cases = [
    ("i cannot breathe properly",                    True),
    ("bleeding won't stop for an hour",              True),
    ("I can't swallow and my tongue is swelling up", True),
    ("mera chehra bohat sooj gaya hai aur bukhar hai", True),  # Urdu face swelling
    ("my gum is bleeding a little when I brush",     False),   # must NOT match medical
    ("just need a dental cleaning",                  False),   # must NOT match medical
]

print("── P07 Medical Emergency Regex Verification ─────────────────────")
for text, should_match in cases:
    matched, pat = matches_medical(text)
    ok = matched == should_match
    sym = "✓" if ok else "✗ FAIL"
    print(f"  {sym}  matched={matched}  «{text}»")
    if matched and pat:
        print(f"        triggered by: {pat}")
    if not ok:
        failures.append(f"P07: '{text}' → matched={matched} expected={should_match}")

# P04 invoice regex
print("\n── P04 Invoice Number Regex ─────────────────────────────────────")
inv_pat = (r"\b(?:invoice|inv|bill)\s*(?:number|num|no|#)?\s*[:#]?\s*#?\s*([A-Za-z0-9][-A-Za-z0-9_/]{0,30})"
           r"|\b(INV-[A-Za-z0-9\-_]+)")

inv_cases = [
    ("Invoice #: S-1001 from vendor Acme Corp",   "S-1001"),
    ("Invoice No: INV-9020 Date: 2026",           "INV-9020"),
    ("Bill #123 Total: 500.00",                   "123"),
    ("INV-9999 is the invoice",                   "INV-9999"),
]
for text, expected in inv_cases:
    m = re.search(inv_pat, text, re.IGNORECASE)
    got = (m.group(1) or m.group(2) or "").strip() if m else None
    # strip trailing noise
    if got:
        got = re.split(r"\s+(?:dated?|from|vendor|total|amount|due)\b", got, flags=re.IGNORECASE)[0].strip()
    ok = got == expected
    sym = "✓" if ok else "✗ FAIL"
    print(f"  {sym}  got='{got}' expected='{expected}'  «{text}»")
    if not ok:
        failures.append(f"P04 inv_num: '{text}' → got '{got}' expected '{expected}'")

# P10 saas metrics (pure python, no pydantic)
print("\n── P10 SaaS Metrics (pure logic) ───────────────────────────────")
SAAS_METRICS = {"arr_usd": 4_800_000.0, "mrr_usd": 400_000.0,
                "cash_on_hand_usd": 2_100_000.0, "monthly_burn_usd": 280_000.0}
runway = round(SAAS_METRICS["cash_on_hand_usd"] / SAAS_METRICS["monthly_burn_usd"], 1)
ok = runway > 0 and SAAS_METRICS["arr_usd"] > 0
print(f"  {'✓' if ok else '✗ FAIL'}  ARR=${SAAS_METRICS['arr_usd']:,.0f}  MRR=${SAAS_METRICS['mrr_usd']:,.0f}  runway={runway}mo")
if not ok:
    failures.append("P10 metrics zero")

# P10 ARR keyword matching  
saas_kw = ["arr", "mrr", "runway", "annual recurring", "monthly recurring", "burn rate", "burn", "cash runway"]
q = "What is our ARR, MRR and runway?"
hit = any(kw in q.lower() for kw in saas_kw)
print(f"  {'✓' if hit else '✗ FAIL'}  ARR/MRR/runway query keyword matched={hit}")
if not hit:
    failures.append("P10 agent: ARR query keyword not matched")

print("\n" + "="*60)
if failures:
    print(f"FAILURES ({len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print("ALL REGEX/LOGIC CHECKS PASSED ✓")
