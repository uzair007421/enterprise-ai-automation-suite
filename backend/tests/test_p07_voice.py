"""
Unit & Integration Tests for Project 07: Dental Voice Appointment Agent
Verifies:
1. High-recall clinical triage for critical dental emergencies.
2. Routine checkup and cleaning classification.
3. Urgent restorative procedure triage.
4. Database appointment booking with SMS notification.
5. Doctor slot conflict prevention (anti-double booking).
"""
import pytest
from core.db import init_db, DatabaseSession
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
    assert res.urgency_tier == "URGENT"

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
        session_id="test_voice_session"
    )

    # First booking: must succeed
    res1 = book_appointment(req1, db=session)
    assert res1.status == "CONFIRMED"
    assert res1.appointment_id.startswith("APPT-")
    assert res1.sms_status in ("live_sent", "sandbox_logged")

    # Second booking: same doctor, same slot time -> must reject due to conflict
    req2 = AppointmentBookingRequest(
        patient_name="Scottie Pippen",
        patient_phone="(555) 998-5678",
        doctor="Dr. Marcus Vance",
        slot_time=slot,
        reason="Crown check",
        is_emergency=False,
        session_id="test_voice_session"
    )

    res2 = book_appointment(req2, db=session)
    assert res2.status == "CONFLICT_REJECTED"
    assert "already booked" in res2.confirmation_message

    session.close()
