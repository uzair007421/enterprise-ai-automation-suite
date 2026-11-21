# 🦷 Project 07: Voice AI Clinic Appointment Agent

> **Commercial Brief:**  
> *"Patients call and our reception is overloaded. Build a voice agent that answers calls, books or reschedules appointments, confirms by SMS, and transfers to staff for emergencies."*

---

## 🌟 Key Capabilities
* **Telephony Voice Dialogue Manager:** Compatible with Vapi, Retell AI, and Twilio Voice SIP trunks.
* **Acute Medical Emergency Triage:** Instantly intercepts traumatic dental emergencies (severe bleeding, knocked-out teeth, airway swelling) and performs immediate blind transfer to clinical staff.
* **Live Practice Calendar Booking:** Queries doctor slot availability (Dr. Sarah Vance & Dr. Michael Chen) and reserves appointments in real-time.
* **Twilio SMS Confirmation Dispatch:** Immediately sends patient address, date, time, and instructions via SMS upon booking.

---

## 🏗️ Architecture & Call Telephony Flow

```
                      [ Patient Inbound Phone Call ]
                                    │
                                    ▼
                 [ Voice AI Speech Recognition & Dialogue ]
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
[ "Bleeding / Trauma" ]     [ "Book Appointment" ]      [ "Reschedule APT" ]
(Severe pain / Accident)     (Doctor & Slot selection)   (Lookup existing slot)
       │                            │                            │
       ▼                            ▼                            ▼
[ EMERGENCY PROTOCOL ]      [ CALENDAR RESERVATION ]    [ CALENDAR RE-ALLOCATION ]
 • Priority Alarm            • Lock Doctor Slot          • Release previous slot
 • Immediate Transfer to     • Assign Appointment ID     • Assign new slot
   Clinical Surgeon Hotline  • Trigger Twilio SMS Conf   • Send SMS Confirmation
```

---

## ⚡ How to Run Live Interactive Demo

Zero external pip dependencies required. Runs completely using Python standard library:

```bash
cd 07-dental-voice-appointment-agent
python run_demo.py
```
Open your browser at: **`http://localhost:8007`**

---

## 🎥 60-Second Fiverr Video Recording Script
1. **(0:00 - 0:15) The Hook:**  
   *"Dental clinics lose up to 40% of new patients to busy signals when receptionists are overloaded. Here is our 24/7 Voice AI Receptionist."*
2. **(0:15 - 0:35) Booking an Appointment & SMS Sync:**  
   Click the preset: *"Book appointment with Dr. Sarah for tomorrow at 10:30 AM"*.  
   Show the Voice Agent speak, reserve the slot on the doctor's calendar, and immediately send a Twilio SMS confirmation!
3. **(0:35 - 0:50) Emergency Triage Protocol:**  
   Click the red preset: *"HELP! Knocked out tooth & severe bleeding!"*  
   Show the instant red emergency transfer badge: *"Notice how the AI immediately detects a clinical emergency, pauses the booking bot, and transfers the call to the emergency desk."*
4. **(0:50 - 1:00) Integration Call to Action:**  
   *"Integrates with Vapi, Retell, Twilio, and Google Calendar. Contact me to deploy Voice AI for your clinic!"*

---

## 💼 Fiverr Proposal Pitch Template

```text
Hi [Client Name],

I specialize in building intelligent Voice AI receptionists for medical and dental practices using Retell AI, Vapi, and Twilio.

I have already developed a comprehensive Voice AI Receptionist system that provides:
1. Natural Conversational Booking: Inbound callers can book, reschedule, or cancel appointments naturally.
2. Direct Practice Calendar Sync: Live doctor slot reservation with zero double-booking risk.
3. Automated Twilio SMS Confirmation: Instant SMS reminders with directions and rescheduling keywords.
4. Acute Emergency Triage Protocol: Automatic detection of severe medical symptoms with instant live staff transfer.

I can set up a live phone number demo for your practice within 4 business days. Let's start a quick chat to discuss your setup!
```

---

## 💰 Recommended Fiverr Gig Pricing
* **Basic ($300 - $500):** Voice AI receptionist for FAQs and office hours over Twilio/Vapi.
* **Standard ($750 - $1,200):** Full Appointment Booking Voice Agent + Google Calendar sync + Twilio SMS confirmation.
* **Premium ($1,800 - $3,500):** Multi-Doctor Practice Voice System + Emergency Transfer Trunk + Practice Management CRM integration (Dentrix / Curve Dental).
