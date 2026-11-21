"""
Code-Level Refund Guardrails & Escalation Ticket Dispatcher
Critical Safety Layer:
1. Pure code-level refund barrier: The AI bot has NO refund execution API or tool available.
2. Automated Human Escalation: Any refund demand or angry sentiment triggers ticket creation in SQLite.
3. Multilingual empathetic policy communication (English & Roman Urdu).
"""
import uuid
import logging
from typing import Tuple, Optional
from datetime import datetime, timezone
from core.db import DatabaseSession
from .schemas import ClassificationResult

logger = logging.getLogger("p03_support.guardrails")

ADVERSARIAL_INJECTION_KEYWORDS = [
    "ignore previous instructions", "system prompt", "developer mode", "override policy",
    "sudo", "grant refund immediately", "transfer money now", "admin refund override"
]

def check_and_apply_refund_guardrail(
    text: str,
    classification: ClassificationResult,
    session_id: str,
    order_id: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Verifies if a refund is requested or an adversarial jailbreak is attempted.
    Returns: (is_blocked, ticket_id, explanation_reply)
    """
    text_lower = text.lower()
    is_adversarial = any(k in text_lower for k in ADVERSARIAL_INJECTION_KEYWORDS)
    is_human_request = any(k in text_lower for k in ["human", "supervisor", "insaan se", "agent se", "representative"])
    is_refund_request = (
        classification.intent == "REFUND_INQUIRY" or
        "refund" in text_lower or
        "paisa wapis" in text_lower or
        "paise wapas" in text_lower or
        "money back" in text_lower or
        is_human_request
    )

    if not is_refund_request and not is_adversarial and not classification.is_angry_escalation:
        return False, None, None

    # Customer requires human intervention
    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    db = DatabaseSession()
    try:
        db.execute(
            """
            INSERT INTO p03_tickets 
            (id, order_id, customer_id, state, sentiment, transcript, escalated_to_human, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                ticket_id,
                order_id or classification.extracted_order_id or "UNKNOWN",
                session_id,
                "OPEN_ESCALATED",
                classification.sentiment,
                text,
                datetime.now(timezone.utc).isoformat()
            )
        )
    finally:
        db.close()

    logger.info(f"Guardrail triggered. Ticket {ticket_id} opened for session {session_id}.")

    # Generate culturally empathetic policy explanation in matched language
    if classification.language == "Roman Urdu":
        if is_refund_request:
            reply = (
                f"Hum samajhtay hain aapki pareshani. Hamari store policy ke mutabiq direct automated refunds allowed nahi hain. "
                f"Aapki inquiry human finance team ko bhej di gayi hai. Aapka ticket number **{ticket_id}** hai. "
                f"Humari support team 2 se 4 ghantay ke andar aapse rabta karegi."
            )
        else:
            reply = (
                f"Aapki pareshani par hum maazrat-khwah hain. Aapka case priority support ke liye escalate kar diya gaya hai. "
                f"Aapka ticket number **{ticket_id}** hai. Hamara agent jald aapse rabta karega."
            )
    else:
        if is_refund_request:
            reply = (
                f"We completely understand your concern. Under our financial security policy, automated AI refunds are strictly prohibited. "
                f"Your request has been safely escalated to our Finance Management Team under Ticket ID **{ticket_id}**. "
                f"A human representative will review your order within 2 to 4 hours."
            )
        else:
            reply = (
                f"We sincerely apologize for the inconvenience caused. Because of the urgency of your issue, "
                f"we have created priority escalation Ticket **{ticket_id}** for our Senior Support Supervisor to resolve."
            )

    return True, ticket_id, reply
