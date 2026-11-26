"""
Unit & Integration Tests for Project 07: Dental Voice Appointment Agent
Verifies:
1. High-recall clinical triage for critical dental emergencies vs routine vs urgent.
2. Mild brushing bleeding classified as ROUTINE_CHECKUP (eliminating over-triage).
3. Severe toothache with fever classified as URGENT_APPOINTMENT (not ER 911).
4. Roman Urdu emergency handling.
5. Dynamic emergency dispatch number from config.
6. SaaS multi-tenant appointment isolation and conflict resolution.
7. Paraphrased / natural-language emergency phrases beyond exact-keyword matching.
   These are REAL audit-identified failing cases now covered by expanded regex patterns.
"""
import pytest
from core.db import init_db, DatabaseSession
from core.config import settings
from projects.p07_voice.triage_engine import triage_dental_inquiry
from projects.p07_voice.router import book_appointment
from projects.p07_voice.schemas import AppointmentBookingRequest

def setup_module(module):
    init_db()

def test_critical_emergency_triage():
    transcript = "Help, I got hit in the face playing basketball, heavy bleeding and my front tooth was knocked out!"
    res = triage_dental_inquiry(transcript)
    assert res.is_emergency is True
    assert res.urgency_tier == "CRITICAL_EMERGENCY"
    assert "bleeding" in res.symptoms_detected or "knocked out" in res.symptoms_detected
    assert "Oral Surgery" in res.suggested_doctor

def test_routine_checkup_triage():
    transcript = "Hi, I would like to schedule my regular 6-month dental cleaning and checkup next Tuesday."
    res = triage_dental_inquiry(transcript)
    assert res.is_emergency is False
    assert res.urgency_tier == "ROUTINE_CHECKUP"
    assert "Elena Rostova" in res.suggested_doctor

def test_urgent_care_triage():
    transcript = "I bit on a hard nut and have a chipped tooth with some sensitivity to cold drinks."
    res = triage_dental_inquiry(transcript)
    assert res.urgency_tier in ("URGENT", "URGENT_APPOINTMENT")

def test_mild_bleeding_on_brushing_is_routine():
    """Audit Fix: 'my gum is bleeding a little when I brush' must be ROUTINE_CHECKUP, NOT critical."""
    transcript = "my gum is bleeding a little when I brush"
    res = triage_dental_inquiry(transcript)
    assert res.urgency_tier == "ROUTINE_CHECKUP"
    assert res.is_emergency is False

def test_severe_toothache_with_fever_is_urgent_care():
    """Audit Fix: 'severe toothache with fever' must be URGENT_APPOINTMENT, NOT critical ER."""
    transcript = "I have a severe toothache with fever"
    res = triage_dental_inquiry(transcript)
    assert res.urgency_tier == "URGENT_APPOINTMENT"
    assert res.is_emergency is False
    assert "Restorative Care" in res.suggested_doctor

def test_dynamic_emergency_number_dispatch(monkeypatch):
    """Audit Fix: Emergency referral dynamically uses settings.EMERGENCY_NUMBER."""
    monkeypatch.setattr(settings, "EMERGENCY_NUMBER", "1122")
    res = triage_dental_inquiry("difficulty breathing and severe chest pain")
    assert res.is_emergency is True
    assert "1122" in res.suggested_doctor
    assert "1122" in res.triage_notes

def test_appointment_booking_and_conflict_resolution():
    import uuid
    slot = f"2026-11-25 14:00-{uuid.uuid4().hex[:6]}"
    session = DatabaseSession()

    req1 = AppointmentBookingRequest(
        patient_name="Michael Jordan",
        patient_phone="(555) 998-1234",
        doctor="Dr. Marcus Vance",
        slot_time=slot,
        reason="Severe abscess and swelling",
        is_emergency=True,
        tenant_id="apex_dental_downtown",
        session_id="test_voice_session"
    )

    # First booking: must succeed
    res1 = book_appointment(req1, db=session)
    assert res1.status == "CONFIRMED"
    assert res1.appointment_id.startswith("APPT-")
    assert res1.sms_status in ("live_sent", "sandbox_logged")

    # Second booking: same doctor, same slot time, same clinic -> must reject due to conflict
    req2 = AppointmentBookingRequest(
        patient_name="Scottie Pippen",
        patient_phone="(555) 998-5678",
        doctor="Dr. Marcus Vance",
        slot_time=slot,
        reason="Crown check",
        is_emergency=False,
        tenant_id="apex_dental_downtown",
        session_id="test_voice_session"
    )

    res2 = book_appointment(req2, db=session)
    assert res2.status == "CONFLICT_REJECTED"
    assert "already booked" in res2.confirmation_message

    session.close()

def test_saas_multi_tenant_clinic_isolation():
    """SaaS Feature: Appointments are isolated by clinic tenant partition."""
    import uuid
    slot = f"2026-11-28 11:00-{uuid.uuid4().hex[:6]}"
    session = DatabaseSession()

    # Clinic North books slot
    req_north = AppointmentBookingRequest(
        patient_name="Patient North",
        patient_phone="(555) 111-2222",
        doctor="Dr. Marcus Vance",
        slot_time=slot,
        reason="Consultation",
        tenant_id="clinic_north",
        session_id="sess_north"
    )
    res_north = book_appointment(req_north, db=session)
    assert res_north.status == "CONFIRMED"

    # Clinic South books same doctor & same time in their own clinic partition -> MUST SUCCEED
    req_south = AppointmentBookingRequest(
        patient_name="Patient South",
        patient_phone="(555) 333-4444",
        doctor="Dr. Marcus Vance",
        slot_time=slot,
        reason="Consultation",
        tenant_id="clinic_south",
        session_id="sess_south"
    )
    res_south = book_appointment(req_south, db=session)
    assert res_south.status == "CONFIRMED"

    session.close()


# ---------------------------------------------------------------------------
# Paraphrase Coverage Tests — Audit Issue #2
# Exact-phrase patterns previously missed these natural-language variants.
# ---------------------------------------------------------------------------

def test_cannot_breathe_properly_is_emergency():
    """'i cannot breathe properly' — paraphrase of breathing emergency."""
    res = triage_dental_inquiry("i cannot breathe properly")
    assert res.is_emergency is True, (
        "FAIL: 'i cannot breathe properly' classified as non-emergency. "
        "Should trigger MEDICAL_EMERGENCY."
    )

def test_bleeding_wont_stop_for_an_hour_is_emergency():
    """'bleeding won't stop for an hour' — prolonged uncontrolled bleeding is a medical emergency."""
    res = triage_dental_inquiry("bleeding won't stop for an hour")
    assert res.is_emergency is True, (
        "FAIL: 'bleeding won't stop for an hour' not classified as emergency. "
        "Should trigger MEDICAL_EMERGENCY (prolonged uncontrolled bleeding)."
    )

def test_tongue_swelling_cannot_swallow_is_emergency():
    """'I can't swallow and my tongue is swelling up' — anaphylaxis/airway emergency."""
    res = triage_dental_inquiry("I can't swallow and my tongue is swelling up")
    assert res.is_emergency is True, (
        "FAIL: Tongue swelling + cannot swallow not classified as emergency. "
        "Should trigger MEDICAL_EMERGENCY (airway compromise)."
    )

def test_urdu_face_swelling_with_fever_triage():
    """'mera chehra bohat sooj gaya hai aur bukhar hai' — Urdu facial swelling + fever."""
    res = triage_dental_inquiry("mera chehra bohat sooj gaya hai aur bukhar hai")
    # Systemic fever + facial swelling = URGENT at minimum (may be MEDICAL_EMERGENCY with airway concern)
    assert res.urgency_tier in ("URGENT_APPOINTMENT", "MEDICAL_EMERGENCY", "CRITICAL_EMERGENCY"), (
        f"FAIL: Urdu facial swelling + fever got '{res.urgency_tier}', expected URGENT or higher."
    )


def test_additional_paraphrased_emergencies_and_non_emergency_precision():
    """Cover choking, air hunger, pouring blood, hardly breathing, and Urdu phrasing without false positives."""
    emergencies = [
        "I am choking",
        "can't get any air",
        "blood keeps pouring from my mouth",
        "I can hardly breathe",
        "the bleeding is not stopping",
        "meri saans phool rahi hai",
        "muh se khoon band nahi ho raha",
        "I can't catch my breath at all",
        "blood is gushing out of my mouth",
        "there is blood everywhere and I feel like passing out",
        "mujhe saans lene mein bohat dikkat ho rahi hai",
        "mere munh se bohat zyada khoon nikal raha hai",
        "zubaan phool gayi hai aur nigalna nahi ho raha",
    ]
    for phrase in emergencies:
        res = triage_dental_inquiry(phrase)
        assert res.is_emergency is True, f"Missed emergency paraphrase: '{phrase}' -> {res.urgency_tier}"

    routines = [
        "I would like to schedule a teeth cleaning next Friday",
        "Can we book a routine checkup for next month?",
        "my gum is bleeding a little when I brush",
        "I am not struggling to breathe, just need a polish",
    ]
    for phrase in routines:
        res = triage_dental_inquiry(phrase)
        assert res.is_emergency is False, f"False emergency alarm on routine: '{phrase}' -> {res.urgency_tier}"


# ---------------------------------------------------------------------------
# Phase 4 Hold-Out Set (42 unseen emergency + 30 non-emergency phrasings)
# Not tuned token-for-token; verifies generalized concept-group recall & precision.
# ---------------------------------------------------------------------------

HOLDOUT_EMERGENCIES = [
    # English varied breathing/airway/bleeding/systemic/trauma/third-person/children
    "My husband is gasping and clutching his chest in the kitchen",
    "She feels faint after endless bleeding from her extraction site",
    "I am unable to get air properly since my face started ballooning",
    "Every time I swallow my throat feels tight and closing",
    "The bleeding has been streaming nonstop for two hours even with cotton",
    "My toddler fell off the stairs and knocked two front teeth out with heavy blood",
    "Patient is barely conscious and lips are turning blue",
    "Mouth is filling up with dark blood clots constantly",
    "Sudden severe allergic reaction after antibiotics and tongue enlarged",
    "Father passed out in the hallway while bleeding from his gums",
    "I keep wheezing whenever I try to lie down after the extraction",
    "Spreading swelling from tooth infection all the way down into my neck",
    "His jaw looks broken and blood is dripping everywhere on his shirt",
    "Cannot talk at all because my tongue puffed up so big",
    "Suffocating feeling since my cheek ballooned up fast this evening",
    "Daughter got hit by a swing, tooth came out and bleeding will not stop",
    "Severe chest tightness and trouble catching a breath",
    "Blood keeps spurting whenever I spit out the gauze",
    "Uncontrolled bleeding after wisdom tooth removal, feeling very dizzy",
    "Facial trauma from bicycle crash with continuous heavy bleeding",
    "Airway feels blocked and I am struggling to breathe",
    "He is unconscious after fainting from severe blood loss",
    "Puffed up face and neck spreading rapidly with high fever",
    "My wife is choking on blood clots after her procedure",
    "Continuous pouring blood from lower socket since noon",
    "Heart racing, dizzy, and swelling closing up my throat",
    # Roman Urdu & mixed English-Urdu (including children / third person)
    "Mere abbu ko saans lene mein bohat mushkil ho rahi hai",
    "Bachay ka daant toot gaya hai aur khoon rukta hi nahi",
    "Gala band ho raha hai aur zubaan sooj rahi hai",
    "Munh mein khoon ke lothre aa rahe hain aur band nahi ho raha",
    "Behosh ho kar gir gayi aur chehra bohat sooj gaya hai",
    "Dant nikal gaya aur khoon lagatar beh raha hai",
    "Saans phool rahi hai aur seene mein dard ho raha hai",
    "Meri ammi ko chakkar aa rahe hain aur khoon bahut beh raha hai",
    "Gardan tak soojan phail rahi hai aur nigalna mushkil hai",
    "Chot lagne se jaw fracture lag raha hai aur khoon band nahi ho raha",
    "Baby is wheezing and choking after swelling started",
    "Khoon ruk nahi raha do ghanton se, dizzy feel ho raha hai",
    "Mera bhai faint ho gaya heavy bleeding ki wajah se",
    "Chehra aur gala tezi se phool raha hai, saans lena hard hai",
    "Cannot breathe cleanly because throat is closing up",
    "Severe blood loss, patient unconscious on the floor",
]

HOLDOUT_NON_EMERGENCIES = [
    # Negations, past resolved symptoms, routine & mild requests
    "I am not having trouble breathing, just want to book a cleaning",
    "No bleeding at all, just looking for a teeth whitening quote",
    "Used to bleed a little last week, now I am fine and want a checkup",
    "She has never had chest pain or fainting, needs a routine exam",
    "Not struggling to breathe, just slight sensitivity to cold water",
    "There is no swelling and no fever, want to reschedule Tuesday",
    "Koi dard ya khoon nahi hai, sirf regular checkup chahiye",
    "My gums bleed slightly when I brush in the morning",
    "Can I book a pediatric fluoride polish next Monday?",
    "Looking to get a cosmetic consultation for veneers",
    "Without any breathing problem or pain, just need an annual exam",
    "My filling came loose yesterday, zero pain or bleeding",
    "I had mild discomfort yesterday, all resolved, booking routine hygiene",
    "Please schedule my daughter's 6-month cleaning appointment",
    "No dizziness, no choking, just curious about invisalign cost",
    "Minor dull ache when chewing ice cream, not severe",
    "Slight bleeding while flossing my back molars",
    "Reschedule my orthodontic consultation to Friday afternoon please",
    "Not choking, no bleeding, just confirming clinic timings",
    "He does not have any bleeding or swelling today",
    "Routine dental scaling and x-ray request for next week",
    "Chipped edge of a crown slightly, no pain and no bleeding",
    "My son needs a school dental checkup certificate next month",
    "Bina kisi takleef ke sirf daant saaf karwane hain",
    "Blood stopped two days ago, feeling totally normal, booking follow-up",
    "Do you accept dental insurance for routine cleanings?",
    "Not fainting, no airway issue, just mild jaw stiffness on waking",
    "Just need a regular checkup for my parents next Thursday",
    "No trouble swallowing, just minor plaque buildup",
    "Are there any morning slots available next week for polishing?",
]


def test_holdout_emergency_recall_and_low_false_alarms():
    """Verify >= 85% recall on 42 unseen hold-out emergencies, <= 2/30 false alarms, and 0 breathing issues routed to ROUTINE."""
    em_hits = 0
    for txt in HOLDOUT_EMERGENCIES:
        res = triage_dental_inquiry(txt)
        if res.is_emergency:
            em_hits += 1
        if any(w in txt.lower() for w in ("breath", "saans", "air", "wheez", "chok", "suffocat")):
            assert res.urgency_tier != "ROUTINE_CHECKUP", f"Breathing inquiry routed to ROUTINE: '{txt}'"

    recall = em_hits / len(HOLDOUT_EMERGENCIES)
    assert recall >= 0.85, f"Hold-out emergency recall {recall:.2%} below 85% ({em_hits}/{len(HOLDOUT_EMERGENCIES)})"

    false_alarms = [txt for txt in HOLDOUT_NON_EMERGENCIES if triage_dental_inquiry(txt).is_emergency]
    assert len(false_alarms) <= 2, f"Too many hold-out false alarms ({len(false_alarms)}): {false_alarms}"
