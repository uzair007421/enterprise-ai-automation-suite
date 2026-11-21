"""
Project 07: Dental Voice Appointment Agent Schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class VoiceTriageRequest(BaseModel):
    transcript: str = Field(description="Patient voice transcript or text input")
    patient_name: Optional[str] = "Walk-in Patient"
    patient_phone: Optional[str] = "(555) 019-2834"
    session_id: Optional[str] = "demo_session"

class VoiceTriageResponse(BaseModel):
    is_emergency: bool
    urgency_tier: str  # "CRITICAL_EMERGENCY" | "URGENT" | "URGENT_APPOINTMENT" | "ROUTINE_CHECKUP"
    intent: str = "ROUTINE_CHECKUP"  # "EMERGENCY" | "URGENT_APPOINTMENT" | "ROUTINE_CHECKUP"
    format: str = "text_only"
    symptoms_detected: List[str]
    suggested_doctor: str
    recommended_slot: str
    triage_notes: str
    confidence: float

class AppointmentBookingRequest(BaseModel):
    patient_name: str
    patient_phone: str
    doctor: str
    slot_time: str
    reason: str
    is_emergency: bool = False
    session_id: Optional[str] = "demo_session"

class AppointmentBookingResponse(BaseModel):
    appointment_id: str
    patient_name: str
    doctor: str
    slot_time: str
    status: str  # "CONFIRMED" | "CONFLICT_REJECTED" | "EMERGENCY_REJECTED"
    is_emergency: bool
    sms_status: str  # "live_sent" | "sandbox_logged" | "not_configured" | "not_sent"
    calendar_sync_status: str  # "live_synced" | "db_persisted" | "conflict" | "not_synced"
    confirmation_message: str
    alternate_slots: List[str] = Field(default_factory=list)
