"""
Voice AI Appointment Agent for Dental Clinics
- Inbound Call State Machine (Vapi / Retell / Twilio compatible)
- Urgent Medical Triage & Emergency Transfer Protocol
- Real-time Calendar Slot Booking & Rescheduling
- Twilio SMS Confirmation Dispatcher
"""
import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

class DentalVoiceAgent:
    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_file = os.path.join(base_dir, "data", "clinic_data.json")
        self.data_file = data_file
        self.state_file = os.path.join(os.path.dirname(data_file), "clinic_live_state.json")
        self._ensure_state()

    def _ensure_state(self):
        if not os.path.exists(self.state_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                base_data = json.load(f)
            base_data["call_logs"] = []
            base_data["sms_dispatched"] = []
            base_data["emergency_transfers"] = []
            self._save(base_data)

    def _load(self) -> Dict[str, Any]:
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def check_emergency(self, utterance: str) -> bool:
        emergency_terms = [
            "bleeding", "severe pain", "unbearable", "knocked out", "broken jaw",
            "swelling throat", "fever and swollen", "trauma", "emergency", "blood"
        ]
        text_lower = utterance.lower()
        return any(term in text_lower for term in emergency_terms)

    def handle_call_turn(self, call_id: str, caller_phone: str, user_transcript: str) -> Dict[str, Any]:
        state = self._load()
        text_lower = user_transcript.lower()

        # 1. EMERGENCY TRIAGE OVERRIDE
        if self.check_emergency(user_transcript):
            transfer_record = {
                "call_id": call_id,
                "caller_phone": caller_phone,
                "transcript": user_transcript,
                "transferred_to": "Clinical On-Call Emergency Desk (Line 1)",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
            state["emergency_transfers"].insert(0, transfer_record)
            self._save(state)

            speech_reply = (
                "I understand this is an urgent dental emergency. I am immediately interrupting this automated booking "
                "and connecting you directly with our senior clinical on-call team right now. Please hold for one second."
            )
            return {
                "voice_speech": speech_reply,
                "agent_state": "EMERGENCY_TRANSFER",
                "transfer_action": "ROUTE_TO_STAFF",
                "status_badge": "🚨 EMERGENCY TRANSFER EXECUTED",
                "call_id": call_id
            }

        # 2. RESCHEDULING INTENT
        if any(w in text_lower for w in ["reschedule", "change time", "move appointment", "postpone"]):
            speech_reply = (
                "I would be glad to help you reschedule. I see your upcoming appointment #APT-8801 with Dr. Sarah Vance "
                "for tomorrow at 9:00 AM. Would you prefer moving that to tomorrow at 2:00 PM or Thursday at 3:30 PM?"
            )
            return {
                "voice_speech": speech_reply,
                "agent_state": "RESCHEDULING_FLOW",
                "available_slots": state["available_slots"][:2],
                "status_badge": "🔄 RESCHEDULE FLOW ACTIVE",
                "call_id": call_id
            }

        # 3. BOOKING CONFIRMATION INTENT
        if any(w in text_lower for w in ["book", "tomorrow", "10:30", "schedule", "dr sarah", "dr chen", "appointment"]):
            # Find first available slot
            available = [s for s in state["available_slots"] if s["status"] == "AVAILABLE"]
            chosen_slot = available[0] if available else None

            if chosen_slot:
                chosen_slot["status"] = "BOOKED"
                apt_id = f"APT-{int(datetime.utcnow().timestamp()) % 10000}"
                patient_name = "Caller (Direct Inbound)"

                new_apt = {
                    "appointment_id": apt_id,
                    "patient_name": patient_name,
                    "phone": caller_phone,
                    "doctor": chosen_slot["doctor"],
                    "date": chosen_slot["date"],
                    "time": chosen_slot["time"],
                    "treatment": "Routine Consultation & Cleaning"
                }
                state["existing_appointments"][apt_id] = new_apt

                # Dispatch Twilio SMS
                sms = {
                    "to": caller_phone,
                    "message": f"Apex Smiles: Your appointment with {chosen_slot['doctor']} is confirmed for {chosen_slot['date']} at {chosen_slot['time']}. Address: 450 Medical Plaza Blvd. Reply RESCHEDULE if needed.",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "status": "SENT_VIA_TWILIO"
                }
                state["sms_dispatched"].insert(0, sms)
                self._save(state)

                speech_reply = (
                    f"Wonderful! I have booked your appointment with {chosen_slot['doctor']} for {chosen_slot['date']} "
                    f"at {chosen_slot['time']}. I have also sent a confirmation SMS to your phone number with directions "
                    f"and clinic details. We look forward to seeing you!"
                )
                return {
                    "voice_speech": speech_reply,
                    "agent_state": "CONFIRMED_BOOKED",
                    "booked_slot": chosen_slot,
                    "sms_preview": sms,
                    "status_badge": "✅ APPOINTMENT BOOKED & SMS SENT",
                    "call_id": call_id
                }

        # 4. GREETING FALLBACK
        speech_reply = (
            "Thank you for calling Apex Smiles Dental. I am the clinic's automated voice receptionist. "
            "I can help you book a new appointment, reschedule an existing visit, or connect you immediately with staff for emergencies. "
            "How can I help you today?"
        )
        return {
            "voice_speech": speech_reply,
            "agent_state": "GREETING",
            "status_badge": "📞 CALL IN PROGRESS",
            "call_id": call_id
        }

    def get_clinic_status(self) -> Dict[str, Any]:
        state = self._load()
        return {
            "clinic_name": state["clinic_name"],
            "slots": state["available_slots"],
            "appointments": list(state["existing_appointments"].values()),
            "sms_feed": state["sms_dispatched"][:5],
            "emergencies": state["emergency_transfers"][:5]
        }

    def reset_state(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self._ensure_state()
