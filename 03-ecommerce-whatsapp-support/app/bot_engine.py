"""
Bilingual WhatsApp AI Support Engine with Shopify Integration & Sentiment Escalation Guardrails
Languages: English & Roman Urdu / Urdu
"""
import json
import os
import re
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

class WhatsAppSupportEngine:
    def __init__(self, data_file: Optional[str] = None):
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_file = os.path.join(base_dir, "data", "shopify_store.json")
        self.data_file = data_file
        self.store = self._load_store()
        self.escalation_log = []

    def _load_store(self) -> Dict[str, Any]:
        with open(self.data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def detect_language(self, text: str) -> str:
        """Detects if message is Urdu/Roman Urdu or English."""
        urdu_keywords = [
            "mera", "meri", "kahan", "kab", "aye", "ayega", "paisa", "wapis", "kharab",
            "bakwas", "dhoka", "chahiye", "krna", "karna", "nahi", "bhejo", "aoa",
            "salam", "shukriya", "bhai", "sharam", "jhoot"
        ]
        text_lower = text.lower()
        words = re.findall(r"\w+", text_lower)
        urdu_hits = sum(1 for w in words if w in urdu_keywords)
        return "URDU" if urdu_hits >= 1 else "ENGLISH"

    def analyze_sentiment(self, text: str) -> Tuple[float, bool, str]:
        """
        Calculates sentiment (-1.0 to +1.0) and detects angry/hostile customer escalation.
        Returns: (sentiment_score, is_angry_escalation, reason)
        """
        anger_patterns = [
            r"\b(scam|fraud|thief|chor|dhoka|cheater|loot|bakwas|worst|terrible|horrible|lawyer|sue|court|shame)\b",
            r"\b(useless|disaster|ridiculous|pathetic|disgusting|bogus|ghatia)\b",
            r"(f\*\*\*|wth|wtf|hell|crap|sh\*t)"
        ]
        text_lower = text.lower()

        is_angry = False
        reasons = []
        for pattern in anger_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                is_angry = True
                reasons.extend(matches)

        # Check for multiple exclamation marks or all caps
        if "!!!" in text or (len(text) > 8 and text.isupper()):
            is_angry = True
            reasons.append("HIGH_AGGRESSION_PUNCTUATION")

        if is_angry:
            score = -0.85
            reason_str = f"Aggressive vocabulary detected: {', '.join(reasons)}"
        elif any(w in text_lower for w in ["delay", "late", "waiting", "masla", "problem", "issue", "damaged", "tuta"]):
            score = -0.35
            reason_str = "Customer experiencing dissatisfaction or friction"
        elif any(w in text_lower for w in ["thanks", "thank", "great", "good", "shukriya", "jazakallah", "awesome"]):
            score = 0.8
            reason_str = "Positive customer tone"
        else:
            score = 0.0
            reason_str = "Neutral inquiry"

        return score, is_angry, reason_str

    def process_message(self, text: str, customer_phone: str = "+923001234567") -> Dict[str, Any]:
        lang = self.detect_language(text)
        sentiment_score, is_angry, sentiment_reason = self.analyze_sentiment(text)
        text_lower = text.lower()

        # Extract order ID if present (e.g. SH-8821 or 8821)
        order_match = re.search(r"\b(?:SH-?)?(\d{4})\b", text.upper())
        detected_order_id = f"SH-{order_match.group(1)}" if order_match else None

        # 1. ESCALATION GUARD: Anger/Hostility
        if is_angry:
            escalation_record = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "phone": customer_phone,
                "trigger_text": text,
                "reason": sentiment_reason,
                "status": "ESCALATED_TO_HUMAN_TIER_2"
            }
            self.escalation_log.append(escalation_record)

            if lang == "URDU":
                reply = (
                    "Main aapki pareshani aur gusse ko samajh sakta hoon aur is takleef ke liye nihayat maazrat khwah hoon. 😔\n\n"
                    "Main fori tor par yeh chat apne Senior Human Support Manager ko transfer kar raha hoon. "
                    "Hamara agent agle 5 se 10 minutes mein aap se live connect kar ke yeh masla hal karega."
                )
            else:
                reply = (
                    "I deeply apologize for the frustration and inconvenience caused to you. 😔\n\n"
                    "I have immediately escalated this conversation to our Senior Human Support Supervisor. "
                    "A human agent has been alerted and will step into this chat within 5 to 10 minutes to resolve your issue personally."
                )

            return {
                "reply": reply,
                "language": lang,
                "sentiment_score": sentiment_score,
                "is_escalated": True,
                "escalation_reason": sentiment_reason,
                "guardrail_triggered": "ANGER_HUMAN_TAKEOVER",
                "detected_order_id": detected_order_id
            }

        # 2. STRICT GUARDRAIL: Refund Demands (Never promise a refund by AI)
        if any(w in text_lower for w in ["refund", "paisa wapis", "paise wapis", "money back", "return money"]):
            if lang == "URDU":
                reply = (
                    "Hamari policy ke mutabiq refund ki approval AI bot ke ikhtiyar mein nahi hoti. 🛡️\n\n"
                    "Agar aapka item damaged ya defective hai, toh return process shuru karne ke liye:\n"
                    "1. Product aur courier parcel ki 2 wazeh tasweerein yahan bhejein.\n"
                    "2. Hamari Quality Inspection Team parcel warehouse pohanchne ke baad 24 hours mein inspection kar ke direct bank account mein refund approve karegi.\n\n"
                    "Kya aap return pickup generate karwana chahte hain?"
                )
            else:
                reply = (
                    "Under our store compliance policies, automated AI agents are strictly restricted from authorizing monetary refunds. 🛡️\n\n"
                    "To initiate a formal return & refund claim:\n"
                    "1. Please share 2 photos of the received item and delivery parcel packaging.\n"
                    "2. Our warehouse quality inspection team will inspect the return upon physical arrival and issue approval within 24-48 business hours.\n\n"
                    "Would you like me to generate a return pickup request with the courier?"
                )

            return {
                "reply": reply,
                "language": lang,
                "sentiment_score": sentiment_score,
                "is_escalated": False,
                "guardrail_triggered": "STRICT_REFUND_COMPLIANCE_ENFORCED",
                "detected_order_id": detected_order_id
            }

        # 3. ORDER TRACKING INTENT
        if detected_order_id or any(w in text_lower for w in ["track", "status", "kahan", "parcel", "order", "delivery"]):
            order_id = detected_order_id or "SH-8821"  # fallback to sample order for demo
            order = self.store["orders"].get(order_id)
            if order:
                if lang == "URDU":
                    reply = (
                        f"📦 *Aapke Order #{order['order_id']} ki Live Status:*\n\n"
                        f"• Status: *{order['status']}*\n"
                        f"• Courier: *{order['carrier']}* (Tracking #: `{order['tracking_number']}`)\n"
                        f"• Estimated Delivery: *{order['estimated_delivery']}*\n"
                        f"• Item: {order['items'][0]['title']}\n"
                        f"• Payment: {order['payment_status']}\n\n"
                        f"Agar aapko mazeed maloomat chahiye toh batayein!"
                    )
                else:
                    reply = (
                        f"📦 *Live Status for Order #{order['order_id']}:*\n\n"
                        f"• Status: *{order['status']}*\n"
                        f"• Courier: *{order['carrier']}* (Tracking #: `{order['tracking_number']}`)\n"
                        f"• Estimated Delivery: *{order['estimated_delivery']}*\n"
                        f"• Item: {order['items'][0]['title']}\n"
                        f"• Payment: {order['payment_status']}\n\n"
                        f"Please let me know if you need any additional details!"
                    )
                return {
                    "reply": reply,
                    "language": lang,
                    "sentiment_score": sentiment_score,
                    "is_escalated": False,
                    "guardrail_triggered": None,
                    "order_data": order,
                    "detected_order_id": order_id
                }

        # 4. RETURN INTENT
        if any(w in text_lower for w in ["return", "exchange", "badalna", "wapsi"]):
            order = self.store["orders"].get("SH-9042")
            if lang == "URDU":
                reply = (
                    "Ji bilkul! Hamare tamam products par 14 se 30 days ki return warranty hoti hai. 🔄\n\n"
                    "Return shuru karne ke liye baraye meherbani apna Order Number aur return ki wajah (size issue ya defective) batayein."
                )
            else:
                reply = (
                    "Certainly! All our products are covered by a 14 to 30 day hassle-free return window. 🔄\n\n"
                    "To proceed, please provide your Order Number and brief reason for return (e.g. size fit or defective item)."
                )
            return {
                "reply": reply,
                "language": lang,
                "sentiment_score": sentiment_score,
                "is_escalated": False,
                "guardrail_triggered": None,
                "detected_order_id": detected_order_id
            }

        # 5. GENERAL GREETING / FAQ FALLBACK
        if lang == "URDU":
            reply = (
                "AOA! Apex Retail WhatsApp Support mein khushamdeed! 🛍️\n\n"
                "Main aapki kis cheez mein madad kar sakta hoon?\n"
                "1. Apne order ki live tracking maloom karna (Order # likhein)\n"
                "2. Product return ya exchange ki maloomat\n"
                "3. Hamari live human team se baat karna"
            )
        else:
            reply = (
                "Hello! Welcome to Apex Retail Customer Support on WhatsApp! 🛍️\n\n"
                "How may I assist you today?\n"
                "1. Check live order status & delivery tracking (Provide Order #)\n"
                "2. Return & replacement assistance\n"
                "3. Connect with a live agent"
            )

        return {
            "reply": reply,
            "language": lang,
            "sentiment_score": sentiment_score,
            "is_escalated": False,
            "guardrail_triggered": None,
            "detected_order_id": detected_order_id
        }
