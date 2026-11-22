"""
Project 07: Dental Voice Appointment Agent Schemas
SaaS Multi-Tenant Contracts for Clinical Triage, Emergency Dispatch, and Dynamic Booking.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class VoiceTriageRequest(BaseModel):
    transcript: str = Field(description="Patient spoken audio transcript from Twilio voice or web intake")
    tenant_id: Optional[str] = Field(default="default_clinic", description="SaaS dental clinic partition")
    session_id: Optional[str] = "demo_session"

class VoiceTriageResponse(BaseModel):
    is_emergency: bool
    urgency_tier: str  # "CRITICAL_EMERGENCY" | "URGENT_APPOINTMENT" | "ROUTINE_CHECKUP"
    intent: str
    format: str = "text_only"
    symptoms_detected: List[str]
    suggested_doctor: str
    recommended_slot: str
    triage_notes: str
    confidence: float
    tenant_id: str = "default_clinic"
    engine: str = "rules"

class AppointmentBookingRequest(BaseModel):
    patient_name: str
    patient_phone: str
    doctor: str
    slot_time: str
    reason: Optional[str] = "General Consultation"
    is_emergency: Optional[bool] = False
    tenant_id: Optional[str] = Field(default="default_clinic", description="SaaS clinic partition")
    session_id: Optional[str] = "demo_session"

class AppointmentBookingResponse(BaseModel):
    appointment_id: str
    tenant_id: str = "default_clinic"
    engine: str = "rules"
    patient_name: str
    doctor: str
    slot_time: str
    status: str  # "CONFIRMED" | "CONFLICT_REJECTED" | "EMERGENCY_REJECTED"
    is_emergency: bool
    sms_status: str
    calendar_sync_status: str
    confirmation_message: str
    alternate_slots: List[str] = []
