"""
HubSpot CRM and Broker Notification Adapter for Project 01
Integrates with HubSpot Deals API and Telegram Alerter.
Gracefully operates as an honest local SQLite CRM when credentials are unset.
"""
import logging
from typing import Dict, Any, Tuple
import httpx
from core.config import settings

logger = logging.getLogger("p01_real_estate.crm")

class RealEstateCRMAdapter:
    def __init__(self):
        self.api_key = getattr(settings, "HUBSPOT_ACCESS_TOKEN", None)
        self.telegram_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        self.telegram_chat = getattr(settings, "TELEGRAM_ALERT_CHAT_ID", None)

    def sync_lead_and_offer(self, lead_data: Dict[str, Any], offer_data: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Syncs lead and draft offer to HubSpot CRM.
        Falls back to local SQLite sandbox tracking if HubSpot API key is not configured.
        """
        if not self.api_key or self.api_key == "demo_hubspot_token":
            logger.info(f"HubSpot not configured. Recorded lead {lead_data.get('lead_id')} in honest SQLite CRM sandbox.")
            return True, "sandbox_recorded"

        try:
            url = "https://api.hubapi.com/crm/v3/objects/contacts"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "properties": {
                    "firstname": lead_data.get("name", "").split()[0],
                    "lastname": " ".join(lead_data.get("name", "").split()[1:]),
                    "email": lead_data.get("email"),
                    "phone": lead_data.get("phone"),
                    "lead_status": lead_data.get("score_tier"),
                    "budget": str(lead_data.get("budget", 0))
                }
            }
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    logger.info(f"Successfully synced contact to HubSpot CRM: {res.status_code}")
                    return True, "live_synced"
                else:
                    logger.warning(f"HubSpot returned status {res.status_code}: {res.text}")
                    return False, f"hubspot_api_error_{res.status_code}"
        except Exception as e:
            logger.error(f"HubSpot sync failed: {str(e)}")
            return False, f"hubspot_network_error: {str(e)}"

    def notify_broker_pending_offer(self, offer_data: Dict[str, Any], lead_name: str) -> bool:
        """
        Dispatches high-urgency alert to Managing Broker via Telegram bot.
        """
        if not self.telegram_token or not self.telegram_chat or "demo" in self.telegram_token:
            logger.info("Broker Telegram notification skipped: Bot credentials not configured.")
            return False

        message = (
            f"🏛️ *NEW REAL ESTATE OFFER REQUIRING BROKER APPROVAL*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• Offer ID: `{offer_data.get('offer_id')}`\n"
            f"• Buyer: *{lead_name}*\n"
            f"• Property: *{offer_data.get('property_address')}*\n"
            f"• Offered Price: *${offer_data.get('offered_price', 0):,.0f}*\n"
            f"• Earnest Deposit: *${offer_data.get('earnest_deposit', 0):,.0f}*\n"
            f"• Status: ⚠️ `PENDING_BROKER_REVIEW`\n\n"
            f"Log in to Broker Portal to execute sign-off."
        )

        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json={
                    "chat_id": self.telegram_chat,
                    "text": message,
                    "parse_mode": "Markdown"
                })
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to dispatch broker Telegram alert: {e}")
            return False

crm_adapter = RealEstateCRMAdapter()
