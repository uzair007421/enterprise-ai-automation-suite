"""
Bilingual Support Bot Router
Mounted under /api/ai/ecommerce-support-bot
"""
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from core.events import event_broker
from core.health import record_project_activity
from core.db import DatabaseSession
from core.security import verify_admin_token, mask_email, mask_phone
from .schemas import CustomerMessageRequest, BotResponse, ClassificationResult
from .classifier import classify_customer_message
from .guardrails import check_and_apply_refund_guardrail
from .shopify_adapter import shopify_adapter
from .telegram_adapter import telegram_adapter

router = APIRouter(prefix="/api/ai/ecommerce-support-bot", tags=["Bilingual E-Commerce Support"])

@router.post("/message", response_model=BotResponse)
def handle_customer_message(request: CustomerMessageRequest):
    """
    Core conversation endpoint.
    Processes English, Urdu, and Roman Urdu; applies refund guardrails,
    queries Shopify for orders, and escalates angry sentiment.
    """
    start_time = time.time()
    record_project_activity("ecommerce-support-bot")
    session_id = request.session_id or "demo_session"

    # Step 1: Real-Time SSE Ingestion Broadcast
    event_broker.publish(session_id, {
        "step": "MESSAGE_INGESTION",
        "detail": f"Received '{request.text[:40]}...' from {request.phone or session_id}",
        "timestamp": time.time()
    })

    # Step 2: Intent & Sentiment Classification
    classification = classify_customer_message(request.text)
    event_broker.publish(session_id, {
        "step": "INTENT_CLASSIFICATION",
        "detail": f"Classified Language: {classification.language} | Intent: {classification.intent} | Sentiment: {classification.sentiment} ({classification.sentiment_score}/100)",
        "timestamp": time.time()
    })

    # Step 3: Refund & Prompt Injection Guardrail
    is_blocked, ticket_id, guardrail_reply = check_and_apply_refund_guardrail(
        text=request.text,
        classification=classification,
        session_id=session_id,
        order_id=classification.extracted_order_id
    )

    order_info = None
    if is_blocked and guardrail_reply:
        reply_text = guardrail_reply
        event_broker.publish(session_id, {
            "step": "GUARDRAIL_TRIGGERED",
            "detail": f"Refund/Escalation guardrail active. Created ticket {ticket_id}",
            "timestamp": time.time()
        })
    else:
        # Step 4: Handle standard conversational intents
        target_order_id = classification.extracted_order_id
        if target_order_id:
            order_info = shopify_adapter.get_order_by_id(target_order_id)

        if classification.intent == "GREETING":
            if classification.language == "Roman Urdu":
                reply_text = "Walaikum Assalam! Main aapka AI support assistant hoon. Main aapki kya madad kar sakta hoon? Agar order track karna hai to order number batayein."
            else:
                reply_text = "Hello! Welcome to our store support. How can I help you today? If you'd like to track an order, please share your order number."

        elif classification.intent == "TRACK_ORDER":
            if order_info:
                if classification.language == "Roman Urdu":
                    reply_text = (
                        f"Aapka order **{order_info['id']}** is waqt **{order_info['status']}** hai. "
                        f"Courier service: **{order_info['courier']}** (Tracking ID: `{order_info['tracking_id']}`). "
                        f"Total amount: ${order_info['total_usd']:.2f}."
                    )
                else:
                    reply_text = (
                        f"Order **{order_info['id']}** is currently **{order_info['status']}**. "
                        f"Shipped via **{order_info['courier']}** (Tracking #: `{order_info['tracking_id']}`). "
                        f"Total order value: ${order_info['total_usd']:.2f}."
                    )
            else:
                if classification.language == "Roman Urdu":
                    reply_text = "Mujhe aapka order number nahi mila ya record mein moujood nahi hai. Barah-e-karam apna 4-digit order number (maslan #1042) batayein."
                else:
                    reply_text = "I couldn't locate that order number. Please provide your 4-digit order ID (e.g. #1042) so I can look up the tracking details."

        elif classification.intent == "CANCEL_ORDER":
            if order_info and order_info.get("status") in ["Delivered", "In Transit"]:
                reply_text = (
                    f"Aapka order {order_info['id']} pehle hi dispatch ho chuka hai, is liye foran cancel nahi ho sakta. "
                    f"Aap delivery ke waqt return request initiate kar saktay hain."
                    if classification.language == "Roman Urdu" else
                    f"Order {order_info['id']} is already in transit and cannot be immediately canceled. "
                    f"You can initiate a return upon delivery."
                )
            else:
                reply_text = (
                    "Order cancellation request darj kar li gayi hai. Hamara warehouse staff isay verify kar raha hai."
                    if classification.language == "Roman Urdu" else
                    "Order cancellation request has been noted. Our warehouse dispatch team is processing it."
                )

        else:
            # Default helpful assistant reply
            if classification.language == "Roman Urdu":
                reply_text = "Aapka sawal darj kar liya gaya hai. Main aapki mazeed kya madad kar sakta hoon?"
            else:
                reply_text = "Thank you for reaching out. Let me know if you need help with orders, tracking, or store policies."

    elapsed = round((time.time() - start_time) * 1000, 2)
    event_broker.publish(session_id, {
        "step": "RESPONSE_DISPATCH",
        "detail": f"Dispatched response in {elapsed}ms",
        "timestamp": time.time()
    })

    return BotResponse(
        session_id=session_id,
        reply_text=reply_text,
        language=classification.language,
        intent=classification.intent,
        sentiment=classification.sentiment,
        sentiment_score=classification.sentiment_score,
        escalated_to_human=is_blocked,
        ticket_id=ticket_id,
        order_data=order_info,
        refund_blocked=is_blocked,
        refund_block_reason="Automated refunds strictly prohibited by financial code gate" if is_blocked else None,
        execution_time_ms=elapsed
    )

@router.get("/orders", dependencies=[Depends(verify_admin_token)])
def get_orders_list(limit: int = 10):
    """Lists orders from Shopify / local SQLite ledger with masked contact details."""
    orders = shopify_adapter.list_recent_orders(limit)
    masked_orders = []
    for o in orders:
        o_copy = dict(o)
        if "customer_email" in o_copy:
            o_copy["customer_email"] = mask_email(o_copy["customer_email"])
        if "customer_phone" in o_copy:
            o_copy["customer_phone"] = mask_phone(o_copy["customer_phone"])
        masked_orders.append(o_copy)
    return {"orders": masked_orders}

@router.get("/tickets", dependencies=[Depends(verify_admin_token)])
def get_escalation_tickets():
    """Lists human escalation tickets created by the sentiment/refund guardrail with masked contact info."""
    db = DatabaseSession()
    try:
        rows = db.fetchall("SELECT * FROM p03_tickets ORDER BY created_at DESC")
        tickets = []
        for r in rows:
            d = dict(r)
            if "customer_phone" in d:
                d["customer_phone"] = mask_phone(d["customer_phone"])
            if "customer_email" in d:
                d["customer_email"] = mask_email(d["customer_email"])
            tickets.append(d)
        return {"total": len(tickets), "tickets": tickets}
    finally:
        db.close()

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Receives Telegram updates and routes to conversation handler."""
    data = await request.json()
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if text and chat_id:
        req = CustomerMessageRequest(
            session_id=f"tg_{chat_id}",
            text=text,
            customer_name=message.get("from", {}).get("first_name", "Telegram User")
        )
        resp = handle_customer_message(req)
        telegram_adapter.send_message(chat_id, resp.reply_text)

    return {"ok": True}
