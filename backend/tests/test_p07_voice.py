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
