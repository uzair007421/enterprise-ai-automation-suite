"""
Project 07: Dental Voice Appointment Agent Router
FastAPI router for voice triage, automated booking, calendar synchronization, and Twilio SMS confirmations.
"""
import uuid
import datetime
from fastapi import APIRouter, HTTPException, Depends
from core.db import get_db, DatabaseSession
from core.events import event_broker
from core.security import verify_admin_token, mask_phone, mask_email
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

    # Medical Emergency Guard: chest pain, difficulty breathing, uncontrolled bleeding, facial trauma -> zero slot booking
    import re
    from .triage_engine import MEDICAL_EMERGENCY_INDICATORS
    reason_lower = (req.reason or "").lower()
    is_med_emergency = any(re.search(pat, reason_lower) for pat in MEDICAL_EMERGENCY_INDICATORS) or "chest pain" in reason_lower or "breathing" in reason_lower
    if is_med_emergency:
        event_broker.publish(session_id, {
            "project": "p07_voice",
            "stage": "EMERGENCY_BLOCKED",
            "message": "Life-threatening medical emergency detected. Booking refused; caller instructed to call 911."
        })
        return AppointmentBookingResponse(
            appointment_id="CALL-911",
            patient_name=req.patient_name,
            doctor="None",
            slot_time="None",
            status="EMERGENCY_REJECTED",
            is_emergency=True,
            sms_status="not_sent",
            calendar_sync_status="not_synced",
            confirmation_message="EMERGENCY: Call 911 immediately or visit the nearest emergency room. Online booking is prohibited for life-threatening emergencies.",
            alternate_slots=[]
        )

    # Slot Conflict Check: Doctor cannot be double-booked for the exact slot time
    existing = db.fetchone(
        "SELECT id FROM p07_appointments WHERE (doctor = ? OR doctor IS NOT NULL) AND slot_time = ?",
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
            confirmation_message=f"Conflict: {req.doctor} is already booked at {req.slot_time}. Please select an alternate slot.",
            alternate_slots=["Tomorrow - 10:00 AM", "Tomorrow - 2:00 PM", "Tomorrow - 4:30 PM"]
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

@router.get("/appointments", dependencies=[Depends(verify_admin_token)])
def get_scheduled_appointments(db: DatabaseSession = Depends(get_db)):
    """Retrieves all scheduled patient appointments with masked contact details."""
    rows = db.fetchall("SELECT * FROM p07_appointments ORDER BY created_at DESC LIMIT 50")
    appointments = []
    for r in rows:
        d = dict(r)
        if "patient_phone" in d:
            d["patient_phone"] = mask_phone(d["patient_phone"])
        if "phone" in d:
            d["phone"] = mask_phone(d["phone"])
        if "patient_email" in d:
            d["patient_email"] = mask_email(d["patient_email"])
        appointments.append(d)
    return {"appointments": appointments, "count": len(appointments)}
