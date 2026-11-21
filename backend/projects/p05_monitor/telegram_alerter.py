"""
Telegram Incident Alert Dispatcher
Sends real-time incident reports to configured Telegram channel/chat.
"""
import logging
import httpx
from core.config import settings
from .schemas import HealingExecutionResult

logger = logging.getLogger("p05_monitor.telegram")

class TelegramAlerter:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_ALERT_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    def dispatch_incident_report(self, result: HealingExecutionResult) -> bool:
        if not self.api_url or not self.chat_id:
            logger.info("Telegram alerting not configured in .env. Skipping external dispatch.")
            return False

        message = (
            f"🚨 *Sentinel Self-Healing Incident Alert*\n\n"
            f"• *Workflow:* `{result.workflow_name}`\n"
            f"• *Fault Injected:* `{result.fault_type}` (HTTP {result.initial_http_status})\n"
            f"• *Remediation Strategy:* `{result.recovery_strategy}`\n"
            f"• *Recovery Time:* `{result.recovery_time_ms}ms` ({result.attempts_required} attempts)\n"
            f"• *Current Status:* `{result.final_status}`\n\n"
            f"📋 *Executive Diagnosis:*\n_{result.diagnosis.plain_english_summary}_"
        )

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "Markdown"
                    }
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to post Telegram incident alert: {e}")
            return False

telegram_alerter = TelegramAlerter()
