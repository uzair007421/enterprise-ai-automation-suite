"""
Project 07: Dental Appointment Intake & Symptom Keyword Routing Engine (Non-Diagnostic Demo)
WARNING: This is a rule-based regex/keyword prototype for scheduling demos.
It is NOT a clinical or medical triage device and must NOT be relied upon for patient safety.
Classifies dental intake transcripts into:
1. Medical Emergency -> Immediate Emergency Number referral.
2. Critical Dental Emergency -> Same-day priority walk-in.
3. Urgent Dental Care -> Same-day scheduled slot.
4. Routine Care -> Routine checkup slot.
"""
import re
from typing import List, Tuple
from core.config import settings
from .schemas import VoiceTriageResponse

def get_emergency_number() -> str:
    """Reads configured emergency dispatch number dynamically from settings."""
    return getattr(settings, "EMERGENCY_NUMBER", "1122")

MEDICAL_EMERGENCY_INDICATORS = [
    # Breathing / Airway Obstruction
    r"\bchest\s+pain\b",
    r"\bdifficulty\s+(?:breathing|breath)\b",
    r"\bshortness\s+of\s+breath\b",
    r"\btrouble\s+(?:with\s+)?breath(?:ing)?\b",
    r"\b(?:can'?t|cannot|unable\s+to)\s+breathe\b",
    r"\b(?:i\s+)?(?:am\s+)?(?:not|cannot|can'?t)\s+breath(?:e|ing)?\s*(?:properly|well|at\s+all)?\b",
    r"\b(?:hard|difficult|hardly|barely|struggl(?:e|ing))\s+(?:to\s+)?breath(?:e|ing)?\b",
    r"\bcan\s+(?:hardly|barely)\s+breathe\b",
    r"\b(?:can'?t|cannot)\s+get\s+(?:enough\s+|any\s+)?air\b",
    r"\bno\s+air\b",
    r"\bchok(?:ing|e|ed)\b",
    r"\bsuffocat(?:ing|e)\b",
    r"\bgasping\b",
    r"\bairway\b",
    # Severe / Non-Stopping Bleeding
    r"\bbleed(?:ing)?\s+(?:is\s+)?(?:won'?t|will\s+not|does\s+not|doesn'?t|not|never)\s+stop(?:ping)?\b",
    r"\bbleeding\s+for\s+(?:an?\s+)?(?:hour|hours|long\s+time|while)\b",
    r"\bwon'?t\s+stop\s+bleed(?:ing)?\b",
    r"\bblood\s+(?:won'?t\s+stop|keeps?\s+(?:pouring|gushing|flowing|streaming))\b",
    r"\bpouring\s+(?:out\s+)?(?:blood|from\s+my\s+mouth)\b",
    r"\bnon[\s-]?stop\s+bleed(?:ing)?\b",
    r"\buncontrolled\s+bleeding\b",
    # Anaphylaxis / Airway Swelling
    r"\btongue\s+(?:is\s+)?(?:swelling|swollen|enlarged)\b",
    r"\bthroat\s+(?:is\s+)?(?:swelling|closing|tightening|closing\s+up)\b",
    r"\b(?:i\s+)?(?:can'?t|cannot)\s+swallow\b",
    r"\bhaving\s+(?:trouble|difficulty|problem)\s+swallow(?:ing)?\b",
    r"\bfacial\s+(?:swelling|trauma|edema)\b",
    r"\bheart\s+attack\b",
    r"\bstroke\b",
    r"\bunconscious(?:ness)?\b",
    r"\bhead\s+injury\b",
    # Roman Urdu emergency phrasing
    r"\bsaans\s+(?:nahi|na)\s+aa\s+rahi\b",
    r"\bsaans\s+(?:phool|ruk|band)\b",
    r"\bsaans\s+lene\s+me\s+(?:masla|takleef)\b",
    r"\bkhoon\s+(?:band|ruk)\s+nahi\s+(?:ho\s+)?raha\b",
    r"\bgala\s+(?:band|ghut)\b",
    r"\b(?:chehra|mera\s+chehra)\s+(?:bohat\s+)?(?:sooj|phool)\b",
    r"\bseene\s+me\s+dard\b",
    r"\bdil\s+ka\s+dora\b",
    r"\bbehosh\b"
]

CRITICAL_DENTAL_INDICATORS = [
    r"\bknocked\s*out\b",
    r"\buncontrolled\s+bleeding\b",
    r"\bheavy\s+bleeding\b",
    r"\bbleeding\s+heavily\b",
    r"\bkhoon\s+bahut\s+beh\s+raha\b",
    r"\bkhoon\s+nahi\s+ruk\s+raha\b",
    r"\bdaant\s+(?:toot\s+gaya|nikal\s+gaya)\b",
    r"\bfractur(?:ed|e)\b",
    r"\bbroken\s+(?:jaw|bone)\b",
    r"\bacute\s+trauma\b"
]
URGENT_DENTAL_INDICATORS = [
    r"\btoothache\b",
    r"\bsevere\s+toothache\b",
    r"\btooth\s+hurts\b",
    r"\bhurts\s+really\s+bad\b",
    r"\babscess\b",
    r"\bswelling\b",
    r"\bswollen\b",
    r"\bexcruciating\b",
    r"\bagonizing\b",
    r"\bunbearable\b",
    r"\bsevere\b",
    r"\binfection\b",
    r"\bfever\b",
    r"\bthrobbing\b",
    r"\bpus\b",
    r"\bchipped\b",
    r"\blost\s+filling\b",
    r"\bcrown\s+fell\b",
    r"\bcracked\s+tooth\b",
    r"\bcan'?t\s+(?:sleep|eat|swallow|open)\b",
    r"\bemergency\b",
    r"\bdaant\s+(?:me\s+)?dard\b",
    r"\bshadeed\s+dard\b",
    r"\bbohat\s+dard\b",
    r"\bsoojan\b",
    r"\baaj\s+(?:ka\s+)?appointment\b"
]

MILD_ORAL_PATTERNS = [
    r"\b(?:bleeding\s+(?:a\s+little|slightly)|slight(?:ly)?\s+bleed(?:ing)?|bleed(?:ing)?\s+(?:a\s+little|slightly)?\s*(?:when|while)?\s*(?:i\s*)?brush(?:ing)?|gum(?:s)?\s+bleed(?:ing)?\s+(?:a\s+little|slightly|when\s+brushing))\b",
    r"\b(?:mild|minor|slight)\s+(?:pain|discomfort|ache)\b",
    r"\bjust\s+(?:need\s+)?(?:a\s+)?(?:cleaning|checkup|routine|consultation)\b"
]

NEGATION_PATTERNS = [
    (r"\b(?:not?\s+(?:having|have|experience|experiencing)?\s*(?:any)?|no|without|never|zero)\s+(?:trouble\s+breathing|difficulty\s+breathing|shortness\s+of\s+breath|chest\s+pain|bleeding|pain|swelling|fever|abscess)\b", " [NEGATED_SYMPTOM] "),
    (r"\b(?:don'?t|doesn'?t|didnt|did\s+not)\s+(?:have|feel)\s*(?:any)?\s+(?:trouble\s+breathing|difficulty\s+breathing|shortness\s+of\s+breath|chest\s+pain|bleeding|pain|swelling|fever)\b", " [NEGATED_SYMPTOM] "),
    (r"\b(?:there\s+is\s+no|is\s+not|are\s+not|have\s+no)\s+(?:bleeding|pain|swelling|fever|trouble\s+breathing)\b", " [NEGATED_SYMPTOM] "),
    (r"\bkoi\s+(?:dard|takleef|khoon|masla)\s+(?:nahi|na)\s+hai\b", " [NEGATED_SYMPTOM] ")
]

def strip_negations(text: str) -> str:
    """Replaces negated symptom phrases so they do not falsely trigger emergency protocols."""
    cleaned = text
    for pat, rep in NEGATION_PATTERNS:
        cleaned = re.sub(pat, rep, cleaned, flags=re.IGNORECASE)
    return cleaned

def triage_dental_inquiry(transcript: str, tenant_id: str = "default_clinic") -> VoiceTriageResponse:
    """
    Evaluates patient inquiry transcript and assigns clinical urgency tier & intent.
    Accurately triages mild brushing bleeding to routine, toothache+fever to urgent care,
    and life-threatening emergencies to dynamic emergency dispatch.
    """
    text_lower = strip_negations(transcript.lower())
    symptoms = []
    emergency_number = get_emergency_number()

    # 1. Life-Threatening Medical Emergencies (Immediate Emergency Dispatch Protocol)
    medical_hits = []
    for pat in MEDICAL_EMERGENCY_INDICATORS:
        if re.search(pat, text_lower):
            matched = re.search(pat, text_lower).group(0)
            medical_hits.append(matched)

    if medical_hits:
        return VoiceTriageResponse(
            is_emergency=True,
            urgency_tier="CRITICAL_EMERGENCY",
            intent="EMERGENCY",
            format="text_only",
            symptoms_detected=list(set(medical_hits)),
            suggested_doctor=f"Call {emergency_number} / Go to Emergency Room",
            recommended_slot=f"CALL_{emergency_number}_IMMEDIATELY",
            triage_notes=f"CRITICAL MEDICAL EMERGENCY: {', '.join(medical_hits)}. Call {emergency_number} immediately or visit the nearest Emergency Room. Online booking is prohibited for medical emergencies.",
            confidence=1.0,
            tenant_id=tenant_id,
            engine="rules"
        )

    # 2. Check for Mild Symptoms (e.g., gum bleeding a little when brushing)
    is_mild = any(re.search(pat, text_lower) for pat in MILD_ORAL_PATTERNS)

    # 3. Critical Dental Emergencies (Acute trauma, knocked out tooth, massive uncontrolled bleeding)
    critical_dental_hits = []
    for pat in CRITICAL_DENTAL_INDICATORS:
        if re.search(pat, text_lower):
            matched = re.search(pat, text_lower).group(0)
            critical_dental_hits.append(matched)

    # 4. Urgent Dental Care (Toothache, toothache with fever, broken crown, abscess)
    urgent_hits = []
    for pat in URGENT_DENTAL_INDICATORS:
        if re.search(pat, text_lower):
            matched = re.search(pat, text_lower).group(0)
            urgent_hits.append(matched)

    if critical_dental_hits and not is_mild:
        tier = "CRITICAL_EMERGENCY"
        intent = "EMERGENCY"
        is_emergency = True
        symptoms.extend(critical_dental_hits)
        suggested_doctor = "Dr. Marcus Vance (Emergency Oral Surgery)"
        recommended_slot = "Today - Immediate Walk-in / On-Call Priority (within 1 hour)"
        notes = f"CRITICAL DENTAL EMERGENCY: Immediate triage required. Patient exhibits acute trauma/bleeding: {', '.join(critical_dental_hits)}."
        confidence = 0.99
    elif urgent_hits and not is_mild:
        tier = "URGENT_APPOINTMENT"
        intent = "URGENT_APPOINTMENT"
        is_emergency = False
        symptoms.extend(urgent_hits)
        suggested_doctor = "Dr. Marcus Vance (Restorative Care)"
        recommended_slot = "Today - 3:30 PM (Urgent Care Reserve)"
        notes = f"URGENT CARE: Same-day slot recommended for symptoms: {', '.join(urgent_hits)}."
        confidence = 0.95
    else:
        tier = "ROUTINE_CHECKUP"
        intent = "ROUTINE_CHECKUP"
        is_emergency = False
        if is_mild:
            symptoms.append("Mild gum sensitivity/bleeding on brushing (prophylaxis/hygiene indicated)")
        else:
            symptoms.append("Routine preventive / cosmetic inquiry")
        suggested_doctor = "Dr. Elena Rostova (Preventive Dentistry)"
        recommended_slot = "Tomorrow - 10:00 AM (Next Available)"
        notes = "Routine appointment scheduled for regular hygiene, prophylaxis, or consultation."
        confidence = 0.96

    return VoiceTriageResponse(
        is_emergency=is_emergency,
        urgency_tier=tier,
        intent=intent,
        format="text_only",
        symptoms_detected=list(set(symptoms)),
        suggested_doctor=suggested_doctor,
        recommended_slot=recommended_slot,
        triage_notes=notes,
        confidence=confidence,
        tenant_id=tenant_id,
        engine="rules"
    )
