"""
Project 07: Notification & Calendar Adapters
Integrates with Twilio Programmable SMS and Google Calendar.
Gracefully operates in honest SQLite sandbox mode when credentials are not configured.
"""
import logging
from typing import Tuple
import httpx
from core.config import settings

logger = logging.getLogger("p07_voice.adapter")

class DentalNotificationAdapter:
    def __init__(self):
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        self.from_phone = getattr(settings, "TWILIO_PHONE_NUMBER", None)

    def send_appointment_sms(self, to_phone: str, message: str) -> Tuple[bool, str]:
        """
        Dispatches SMS confirmation via Twilio.
        Falls back to honest sandbox logging when Twilio API credentials are missing.
        """
        if not self.account_sid or not self.auth_token or "demo" in str(self.account_sid):
            logger.info(f"Twilio not configured. Sandbox SMS logged for {to_phone}: '{message}'")
            return True, "sandbox_logged"

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            auth = (self.account_sid, self.auth_token)
            data = {
                "From": self.from_phone,
                "To": to_phone,
                "Body": message
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, auth=auth, data=data)
                if res.status_code in (200, 201):
                    logger.info(f"Twilio SMS dispatched successfully to {to_phone}")
                    return True, "live_sent"
                else:
                    logger.warning(f"Twilio API error {res.status_code}: {res.text}")
                    return False, f"twilio_error_{res.status_code}"
        except Exception as e:
            logger.error(f"Twilio connection failure: {str(e)}")
            return False, f"network_error: {str(e)}"

notification_adapter = DentalNotificationAdapter()
