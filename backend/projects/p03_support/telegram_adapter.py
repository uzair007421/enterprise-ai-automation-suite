"""
Telegram Bot Webhook & Message Dispatch Adapter
Receives messages via Telegram Webhook and responds in real-time.
"""
import logging
from typing import Dict, Any, Optional
import httpx
from core.config import settings

logger = logging.getLogger("p03_support.telegram")

class TelegramAdapter:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    def send_message(self, chat_id: int, text: str) -> bool:
        if not self.api_url:
            logger.info(f"Telegram not configured. Message for chat_id={chat_id} skipped: {text[:40]}...")
            return False

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.api_url}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to dispatch Telegram message: {e}")
            return False

telegram_adapter = TelegramAdapter()
