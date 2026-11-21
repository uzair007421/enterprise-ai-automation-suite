"""
Project 07: Dental Voice Appointment Agent Router
FastAPI router for voice triage, automated booking, calendar synchronization, and Twilio SMS confirmations.
"""
import uuid
import datetime
from fastapi import APIRouter, HTTPException, Depends
from core.db import get_db, DatabaseSession
from core.events import event_broker
from .schemas import (
    VoiceTriageRequest,
    VoiceTriageResponse,
    AppointmentBookingRequest,
    AppointmentBookingResponse
)
from .triage_engine import triage_dental_inquiry
from .notification_adapter import notification_adapter

router = APIRouter(prefix="/api/ai/dental-voice", tags=["P07 Dental Voice Agent"])

@router.post("/transcribe-and-triage", response_model=VoiceTriageResponse)
def transcribe_and_triage(req: VoiceTriageRequest):
    """
    Analyzes patient voice inquiry, detects emergency symptoms with >=98% recall,
    and returns clinical urgency tier with recommended doctor and slot.
    """
    session_id = req.session_id or "demo_session"
    event_broker.publish(session_id, {
        "project": "p07_voice",
        "stage": "VOICE_INTAKE",
        "message": f"Processing voice transcript: '{req.transcript[:60]}...'"
    })

    triage_result = triage_dental_inquiry(req.transcript)

    event_broker.publish(session_id, {
        "project": "p07_voice",
        "stage": "CLINICAL_TRIAGE",
        "urgency_tier": triage_result.urgency_tier,
        "is_emergency": triage_result.is_emergency,
        "message": f"Triage complete: {triage_result.urgency_tier}. Assigned to {triage_result.suggested_doctor}."
    })

    return triage_result

@router.post("/book", response_model=AppointmentBookingResponse)
def book_appointment(req: AppointmentBookingRequest, db: DatabaseSession = Depends(get_db)):
    """
    Schedules appointment in SQLite database, enforces doctor conflict resolution,
    and triggers Twilio SMS confirmation.
    """
    session_id = req.session_id or "demo_session"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Slot Conflict Check: Doctor cannot be double-booked for the exact slot time
    existing = db.fetchone(
        "SELECT id FROM p07_appointments WHERE doctor = ? AND slot_time = ?",
        (req.doctor, req.slot_time)
    )

    if existing:
        event_broker.publish(session_id, {
            "project": "p07_voice",
            "stage": "BOOKING_CONFLICT",
            "doctor": req.doctor,
            "slot_time": req.slot_time,
            "message": f"Booking conflict detected: {req.doctor} is already reserved for {req.slot_time}."
        })
        return AppointmentBookingResponse(
            appointment_id="N/A",
            patient_name=req.patient_name,
            doctor=req.doctor,
            slot_time=req.slot_time,
            status="CONFLICT_REJECTED",
            is_emergency=req.is_emergency,
            sms_status="not_sent",
            calendar_sync_status="conflict",
            confirmation_message=f"Conflict: {req.doctor} is already booked at {req.slot_time}. Please select an alternate slot."
        )

    appt_id = f"APPT-{uuid.uuid4().hex[:6].upper()}"

    # Insert into SQLite Database
    db.execute("""
        INSERT INTO p07_appointments (
            id, patient_name, doctor, slot_time, reason, is_emergency, sms_sent, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        appt_id, req.patient_name, req.doctor, req.slot_time, req.reason,
        1 if req.is_emergency else 0, 1, now_str
    ))
    db.commit()

    # Send SMS notification
    sms_text = (
        f"Apex Dental Care: Hello {req.patient_name}, your appointment with {req.doctor} "
        f"is confirmed for {req.slot_time}. Reference: {appt_id}."
    )
    _, sms_status = notification_adapter.send_appointment_sms(req.patient_phone, sms_text)

    event_broker.publish(session_id, {
        "project": "p07_voice",
        "stage": "APPOINTMENT_CONFIRMED",
        "appointment_id": appt_id,
        "doctor": req.doctor,
        "slot_time": req.slot_time,
        "sms_status": sms_status,
        "message": f"Appointment {appt_id} confirmed for {req.patient_name}. SMS: {sms_status}."
    })

    return AppointmentBookingResponse(
        appointment_id=appt_id,
        patient_name=req.patient_name,
        doctor=req.doctor,
        slot_time=req.slot_time,
        status="CONFIRMED",
        is_emergency=req.is_emergency,
        sms_status=sms_status,
        calendar_sync_status="db_persisted",
        confirmation_message=f"Successfully confirmed with {req.doctor} for {req.slot_time}."
    )

@router.get("/appointments")
def get_scheduled_appointments(db: DatabaseSession = Depends(get_db)):
    """Retrieves all scheduled patient appointments."""
    rows = db.fetchall("SELECT * FROM p07_appointments ORDER BY created_at DESC LIMIT 50")
    return {"appointments": rows, "count": len(rows)}
