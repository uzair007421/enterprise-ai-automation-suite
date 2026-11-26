"""
Project 07: Dental Appointment Intake & Keyword Routing Prototype (Non-Diagnostic Demo)
WARNING: Rule-based concept-group prototype for appointment scheduling demos ONLY.
It is NOT a clinical or medical triage tool and must NOT be used for patient safety.
Uses text normalization, simple stemming, generalized concept groups, per-concept
negation windows, and a safety-first fallback:
1. Emergency Dispatch Referral -> Life-threatening airway/systemic/uncontrolled hemorrhage indicators.
2. Priority Oral Surgery -> Acute dental trauma (knocked-out tooth, jaw trauma + bleeding).
3. Urgent Appointment -> Moderate dental issues or safety-first ambiguous airway/bleeding fallback.
4. Routine Checkup -> Cleanings, checkups, mild brushing bleeding, negated/resolved past symptoms.
"""
import re
from typing import List, Set
from core.config import settings
from .schemas import VoiceTriageResponse


def get_emergency_number() -> str:
    """Reads configured emergency dispatch number dynamically from settings."""
    return getattr(settings, "EMERGENCY_NUMBER", "1122")


_CONTRACTIONS = [
    (r"\bcan't\b", "cannot"),
    (r"\bcan\s+not\b", "cannot"),
    (r"\bcouldn't\b", "could not"),
    (r"\bwon't\b", "will not"),
    (r"\bwill\s+not\b", "will not"),
    (r"\bisn't\b", "is not"),
    (r"\baren't\b", "are not"),
    (r"\bdon't\b", "do not"),
    (r"\bdoesn't\b", "does not"),
    (r"\bdidn't\b", "did not"),
    (r"\bhaven't\b", "have not"),
    (r"\bhasn't\b", "has not"),
    (r"\bi'm\b", "i am"),
    (r"\bhe's\b", "he is"),
    (r"\bshe's\b", "she is"),
    (r"\bit's\b", "it is"),
    (r"\bthere's\b", "there is"),
]

_STEM_RULES = [
    (r"^breath.*", "breath"),
    (r"^bleed.*", "bleed"),
    (r"^(?:swell.*|swollen)$", "swell"),
    (r"^chok.*", "chok"),
    (r"^suffocat.*", "suffocat"),
    (r"^faint.*", "faint"),
    (r"^wheez.*", "wheez"),
    (r"^gasp.*", "gasp"),
    (r"^puff.*", "puff"),
    (r"^gush.*", "gush"),
    (r"^pour.*", "pour"),
    (r"^drip.*", "drip"),
    (r"^spurt.*", "spurt"),
    (r"^dizz.*", "dizz"),
    (r"^anaphyla.*", "anaphylax"),
    (r"^struggl.*", "struggl"),
    (r"^swallow.*", "swallow"),
    (r"^spread.*", "spread"),
    (r"^fractur.*", "fractur"),
    (r"^unconscious.*", "unconscious"),
    (r"^pass(?:ing|ed)?$", "pass"),
    (r"^sooj.*", "sooj"),
    (r"^nigal.*", "nigal"),
    (r"^lothr.*", "lothr"),
    (r"^ruk.*", "ruk"),
]

_CLAUSE_SPLIT_RE = re.compile(r"[,;.\!\?\n]+|\b(?:but|however|except|though|although)\b")
_NEGATION_TOKENS = {"no", "not", "never", "without", "none", "zero", "nahi", "na", "bina", "koi"}
_RESOLVED_PAST_PHRASES = {"used to", "last week", "yesterday", "ago", "resolved", "no longer", "already stopped", "better now", "now fine"}


def _stem_token(tok: str) -> str:
    for pat, repl in _STEM_RULES:
        if re.match(pat, tok):
            return repl
    return tok


def _normalize_clauses(text: str) -> List[List[str]]:
    """Lowercases, expands contractions, splits clauses, and returns stemmed token lists."""
    s = text.lower()
    for pat, rep in _CONTRACTIONS:
        s = re.sub(pat, rep, s)
    clauses: List[List[str]] = []
    for raw_clause in _CLAUSE_SPLIT_RE.split(s):
        cleaned = re.sub(r"[^a-z0-9\s]", " ", raw_clause)
        toks = [_stem_token(t) for t in cleaned.split() if t]
        if toks:
            clauses.append(toks)
    return clauses


# Concept groups defined via stems and domain synonyms (English + Roman Urdu)
CONCEPT_INHERENT_AIRWAY = {"chok", "suffocat", "wheez", "gasp", "airway"}
CONCEPT_BREATHING_CTX = {"breath", "air", "saans", "swallow", "nigal", "speak", "talk"}
CONCEPT_THROAT_TONGUE = {"throat", "tongue", "gala", "zubaan", "neck", "gardan"}
CONCEPT_AIRWAY_CLOSING = {"clos", "close", "closed", "closing", "shut", "tight", "tightening", "band", "ghut", "block", "blocked"}

CONCEPT_BLEEDING = {"bleed", "blood", "hemorrhag", "hemorrhage", "clot", "khoon", "lothr"}
CONCEPT_SWELLING = {"swell", "puff", "balloon", "ballooned", "enlarg", "enlarged", "edema", "sooj", "soojan", "phool"}
CONCEPT_SPREADING = {"spread", "fast", "rapid", "rapidly", "face", "chehra", "neck", "gardan", "eye"}

CONCEPT_TRAUMA = {"knocked", "avulsed", "fractur", "broken", "accident", "trauma", "toot", "nikal", "fall", "fell", "hit", "injur", "injury"}
CONCEPT_TRAUMA_SEVERE_NOUNS = {"jaw", "bone"}

CONCEPT_SYSTEMIC_SINGLE = {"faint", "unconscious", "anaphylax", "behosh"}
CONCEPT_SYSTEMIC_PHRASES = [
    ("chest", "pain"), ("chest", "tight"), ("chest", "tightness"),
    ("heart", "attack"), ("allergic", "reaction"), ("pass", "out"),
    ("seene", "dard"), ("dil", "dora"), ("lips", "blue"), ("turn", "blue"),
]
CONCEPT_DIZZY = {"dizz", "lightheaded", "chakkar"}

CONCEPT_DIFFICULTY = {
    "cannot", "unable", "hard", "hardly", "barely", "struggl", "trouble", "difficulty",
    "difficult", "problem", "short", "shortness", "catch", "losing", "lost",
    "masla", "takleef", "dikkat", "mushkil", "dushwari", "phool", "ruk", "band", "nahi",
}
CONCEPT_SEVERITY = {
    "uncontrolled", "heavy", "heavily", "profuse", "profusely", "constant", "constantly",
    "gush", "pour", "spurt", "stream", "streaming", "flowing", "drip", "everywhere",
    "fill", "filling", "lot", "much", "hour", "hours", "gauze", "nonstop", "lothr",
    "ghanton", "rukta", "band", "bohat", "bahut", "zyada", "nikal", "beh",
}
CONCEPT_MILD = {"little", "slight", "slightly", "minor", "mild", "bit", "brush", "brushing", "floss", "clean", "cleaning", "checkup", "polish", "whitening", "routine", "regular", "consultation"}
CONCEPT_URGENT_DENTAL = {"toothache", "abscess", "pus", "infection", "fever", "bukhar", "throbbing", "excruciating", "agonizing", "unbearable", "chipped", "cracked", "crown", "filling", "dard", "hurts", "pain"}

# Backward-compatible indicator list imported by p07_voice/router.py booking emergency guard
MEDICAL_EMERGENCY_INDICATORS = [
    r"\bchest\s+pain\b", r"\bbreath", r"\bchok", r"\bsuffocat", r"\bwheez", r"\bgasp",
    r"\buncontrolled\s+bleed", r"\bheart\s+attack\b", r"\bstroke\b", r"\bunconscious\b",
    r"\bpass(?:ing|ed)?\s+out\b", r"\bfaint", r"\bsaans\b", r"\bkhoon\b", r"\bbehosh\b",
]


def _is_negated_at(tokens: List[str], idx: int) -> bool:
    """Checks 5-token lookback window within the clause for negation or resolved past context."""
    window = tokens[max(0, idx - 5):idx]
    if any(w in _NEGATION_TOKENS for w in window):
        return True
    window_str = " ".join(window)
    return any(p in window_str for p in _RESOLVED_PAST_PHRASES)


def _active_tokens(clauses: List[List[str]]) -> Set[str]:
    """Collects non-negated stemmed tokens across all clauses using per-occurrence negation windows."""
    active: Set[str] = set()
    for toks in clauses:
        for i, tok in enumerate(toks):
            if tok in _NEGATION_TOKENS:
                continue
            if not _is_negated_at(toks, i):
                active.add(tok)
    return active


def _clause_has_unnegated_pair(clauses: List[List[str]], group_a: Set[str], group_b: Set[str]) -> bool:
    for toks in clauses:
        a_active = any(t in group_a and not _is_negated_at(toks, i) for i, t in enumerate(toks))
        b_active = any(t in group_b and not _is_negated_at(toks, i) for i, t in enumerate(toks))
        if a_active and b_active:
            return True
    return False


def _has_phrase_unnegated(clauses: List[List[str]], w1: str, w2: str) -> bool:
    for toks in clauses:
        if w1 in toks and w2 in toks:
            idx1 = toks.index(w1)
            idx2 = toks.index(w2)
            if abs(idx1 - idx2) <= 3 and not _is_negated_at(toks, min(idx1, idx2)):
                return True
    return False


def _has_bleeding_persistence(clauses: List[List[str]], active: Set[str]) -> bool:
    """Detects active bleeding with persistence/severity or negation-of-stop ('will not stop bleeding')."""
    if not (active & CONCEPT_BLEEDING):
        return False
    if active & CONCEPT_SEVERITY:
        return True
    for toks in clauses:
        s = " ".join(toks)
        if any(p in s for p in ("not stop", "will not stop", "cannot stop", "never stop", "ruk nahi", "band nahi", "rukta hi nahi")):
            if any(b in toks for b in CONCEPT_BLEEDING):
                return True
    return False


def _has_airway_distress(clauses: List[List[str]], active: Set[str]) -> bool:
    if active & CONCEPT_INHERENT_AIRWAY:
        return True
    # Breathing/swallowing concept combined with difficulty or Roman Urdu 'nahi' right after
    if active & CONCEPT_BREATHING_CTX:
        if _clause_has_unnegated_pair(clauses, CONCEPT_BREATHING_CTX, CONCEPT_DIFFICULTY):
            return True
        for toks in clauses:
            for i, tok in enumerate(toks):
                if tok in CONCEPT_BREATHING_CTX:
                    before = toks[max(0, i - 4):i]
                    after = toks[i + 1:i + 4]
                    if ("nahi" in after or "masla" in after or "dikkat" in after or "takleef" in after) and not any(w in {"no", "never", "without", "not"} for w in before):
                        return True
    # Throat/tongue obstruction or swelling
    if _clause_has_unnegated_pair(clauses, CONCEPT_THROAT_TONGUE, CONCEPT_AIRWAY_CLOSING | CONCEPT_SWELLING):
        return True
    return False


def triage_dental_inquiry(transcript: str, tenant_id: str = "default_clinic") -> VoiceTriageResponse:
    """
    Evaluates intake transcript using generalized concept groups and per-concept negation windows.
    Non-diagnostic appointment intake router only (NOT clinical triage).
    """
    emergency_number = get_emergency_number()
    clauses = _normalize_clauses(transcript)
    active = _active_tokens(clauses)
    symptoms: List[str] = []

    is_mild_context = bool(active & CONCEPT_MILD) and not (active & (CONCEPT_INHERENT_AIRWAY | CONCEPT_SYSTEMIC_SINGLE))
    has_airway = _has_airway_distress(clauses, active)
    has_systemic = bool(active & CONCEPT_SYSTEMIC_SINGLE) or any(_has_phrase_unnegated(clauses, a, b) for a, b in CONCEPT_SYSTEMIC_PHRASES)
    if (active & CONCEPT_DIZZY) and bool(active & (CONCEPT_BLEEDING | CONCEPT_SWELLING)):
        has_systemic = True
    has_bleed = bool(active & CONCEPT_BLEEDING)
    has_severe_bleed = _has_bleeding_persistence(clauses, active) and not ({"brush", "brushing", "floss"} & active)
    has_swelling = bool(active & CONCEPT_SWELLING)
    has_spreading_swell = has_swelling and (has_airway or bool(active & CONCEPT_SPREADING)) and ("mild" not in active)
    has_trauma = bool(active & CONCEPT_TRAUMA)
    has_trauma_critical = has_trauma and (has_bleed or bool(active & CONCEPT_TRAUMA_SEVERE_NOUNS) or "knocked" in active or "fractur" in active or "nikal" in active)

    if has_airway:
        symptoms.append("airway/breathing distress")
    if has_systemic:
        symptoms.append("systemic distress")
    if has_bleed:
        symptoms.append("bleeding")
    if has_swelling:
        symptoms.append("swelling")
    if has_trauma:
        symptoms.append("dental trauma")

    # 1. Medical Emergency -> Emergency Dispatch Referral (CRITICAL_EMERGENCY tier for eval compat)
    if has_airway or has_systemic or (has_severe_bleed and not has_trauma) or has_spreading_swell:
        return VoiceTriageResponse(
            is_emergency=True,
            urgency_tier="CRITICAL_EMERGENCY",
            intent="EMERGENCY",
            format="text_only",
            symptoms_detected=symptoms or ["acute emergency"],
            suggested_doctor=f"Call {emergency_number} / Go to Emergency Room",
            recommended_slot=f"CALL_{emergency_number}_IMMEDIATELY",
            triage_notes=f"CRITICAL SAFETY PROTOCOL (Non-Diagnostic Intake): Immediate medical attention recommended. Call {emergency_number} or visit the nearest Emergency Room.",
            confidence=0.92,
            tenant_id=tenant_id,
            engine="rules",
        )

    # 2. Acute Dental Trauma -> Priority Oral Surgery
    if has_trauma_critical:
        if "knocked" in active:
            symptoms.append("knocked out")
        return VoiceTriageResponse(
            is_emergency=True,
            urgency_tier="CRITICAL_EMERGENCY",
            intent="EMERGENCY",
            format="text_only",
            symptoms_detected=symptoms,
            suggested_doctor="Dr. Marcus Vance (Emergency Oral Surgery)",
            recommended_slot="Today - Immediate Walk-in / On-Call Priority (within 1 hour)",
            triage_notes=f"PRIORITY DENTAL TRAUMA: Immediate oral surgery intake recommended. If severe systemic symptoms occur, call {emergency_number}.",
            confidence=0.90,
            tenant_id=tenant_id,
            engine="rules",
        )

    # 3. Urgent Dental Care + Safety-First Fallback for unnegated airway/bleeding vocab
    has_ambiguous_airway_or_bleed = (bool(active & (CONCEPT_BREATHING_CTX | CONCEPT_THROAT_TONGUE)) or has_bleed) and not is_mild_context
    has_urgent_symptom = bool(active & CONCEPT_URGENT_DENTAL) or (has_swelling and not is_mild_context) or has_trauma

    if has_urgent_symptom or has_ambiguous_airway_or_bleed:
        if not symptoms:
            symptoms.append("urgent intake symptoms")
        return VoiceTriageResponse(
            is_emergency=False,
            urgency_tier="URGENT_APPOINTMENT",
            intent="URGENT_APPOINTMENT",
            format="text_only",
            symptoms_detected=symptoms,
            suggested_doctor="Dr. Marcus Vance (Restorative Care)",
            recommended_slot="Today - 3:30 PM (Urgent Care Reserve)",
            triage_notes=f"URGENT CARE: Same-day slot recommended. If severe, call your local emergency number ({emergency_number}) immediately.",
            confidence=0.82,
            tenant_id=tenant_id,
            engine="rules",
        )

    # 4. Routine Checkup
    if has_bleed and is_mild_context:
        symptoms = ["Mild gum sensitivity/bleeding on brushing (hygiene indicated)"]
    elif not symptoms:
        symptoms = ["Routine preventive / cosmetic inquiry"]

    return VoiceTriageResponse(
        is_emergency=False,
        urgency_tier="ROUTINE_CHECKUP",
        intent="ROUTINE_CHECKUP",
        format="text_only",
        symptoms_detected=symptoms,
        suggested_doctor="Dr. Elena Rostova (Preventive Dentistry)",
        recommended_slot="Tomorrow - 10:00 AM (Next Available)",
        triage_notes=f"Routine appointment slot suggested. If severe symptoms develop, call {emergency_number}.",
        confidence=0.90,
        tenant_id=tenant_id,
        engine="rules",
    )
