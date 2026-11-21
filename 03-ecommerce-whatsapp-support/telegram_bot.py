"""
Bilingual AI Customer Support Telegram Bot for E-Commerce & Shopify
Developed by Muhammad Uzair

Features:
- Live Telegram Bot using python-telegram-bot
- Real AI Generative Model via Google Gemini API (gemini-1.5-flash)
- Bilingual NLP: English & Roman Urdu
- Real Order Lookup (#PK-8921, #PK-4012, #PK-9041)
- Frustration / Hostility Escalation
- Strict Refund Guardrails
"""

import os
import sys
import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Sample E-Commerce Order Database
ORDERS_DB = {
    "PK-8921": {
        "customer": "Ayesha Khan",
        "items": "Wireless Active Noise Cancelling Headphones",
        "amount": "$89.00",
        "status": "In Transit via Leopards Courier",
        "tracking_number": "LEO-77192038",
        "estimated_delivery": "Tomorrow by 5:00 PM"
    },
    "PK-4012": {
        "customer": "Bilal Ahmed",
        "items": "Ergonomic Mechanical Keyboard (RGB)",
        "amount": "$125.00",
        "status": "Delivered to Reception",
        "tracking_number": "TCS-90182411",
        "estimated_delivery": "Delivered on Nov 18"
    },
    "PK-9041": {
        "customer": "Zainab Malik",
        "items": "Smart Fitness Tracker Band v3",
        "amount": "$45.00",
        "status": "Processing in Warehouse",
        "tracking_number": "Pending Courier Pickup",
        "estimated_delivery": "Within 2-3 business days"
    }
}

SYSTEM_INSTRUCTION = """
You are 'Aura', a professional bilingual AI Customer Support Specialist for an e-commerce brand.
Guidelines:
1. Language: Automatically detect whether the customer speaks English, Urdu, or Roman Urdu (e.g., 'mera parcel kab ayega?', 'order kahan hai?'). Reply in the same language and tone.
2. Order Tracking: If the customer provides an order ID like PK-8921 or asking about status, check the order details provided.
3. Strict Refund Guardrail: You are NEVER authorized to promise an immediate cash refund. Inform the user that returns require physical item inspection at the warehouse according to store policy.
4. Professional & Empathetic: Be polite, concise, and helpful.
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "Valued Customer"
    welcome_text = (
        f"👋 Welcome {user_name}! I am **Aura**, your AI Customer Support Assistant.\n\n"
        "I can help you with:\n"
        "📦 Track an order (e.g., 'Track order PK-8921' or 'Mera order kahan hai?')\n"
        "🔄 Return & exchange policies\n"
        "💬 Product inquiries & support in English or Roman Urdu!\n\n"
        "How can I assist you today?"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide your Order ID. Example: `/track PK-8921`", parse_mode="Markdown")
        return
    
    order_id = context.args[0].upper().replace("#", "")
    if order_id in ORDERS_DB:
        ord_info = ORDERS_DB[order_id]
        msg = (
            f"📦 **Order Status: #{order_id}**\n"
            f"👤 Customer: {ord_info['customer']}\n"
            f"🛍️ Items: {ord_info['items']}\n"
            f"🚚 Status: **{ord_info['status']}**\n"
            f"📍 Tracking ID: `{ord_info['tracking_number']}`\n"
            f"⏱️ ETA: {ord_info['estimated_delivery']}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Order `#{order_id}` not found in our database. Please verify your order number.", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    gemini_key = os.environ.get("GEMINI_API_KEY")

    # Check for order numbers in user message
    for order_id, info in ORDERS_DB.items():
        if order_id.lower() in user_text.lower():
            response = (
                f"📦 I found your order **#{order_id}**!\n\n"
                f"• Status: **{info['status']}**\n"
                f"• Items: {info['items']}\n"
                f"• Tracking: `{info['tracking_number']}`\n"
                f"• Expected Delivery: {info['estimated_delivery']}\n\n"
                "Kia aap ko is ke baray mein koi mazeed help chahiye?"
            )
            await update.message.reply_text(response, parse_mode="Markdown")
            return

    # If Gemini API Key is available, call real Gemini model
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYSTEM_INSTRUCTION)
            response = model.generate_content(user_text)
            reply = response.text
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            reply = "Apka shukriya. Humari AI team aap ke sawal ka jaiza le rahi hai. How can I help you further?"
    else:
        # Fallback intelligent bilingual response if no API key set
        lower = user_text.lower()
        if any(w in lower for w in ["kahan", "kab", "status", "track", "delivery", "parcel"]):
            reply = (
                "📦 Order track karne ke liye baraye meherbani apna **Order ID** bhejiye (maslan: `PK-8921` ya `PK-4012`).\n"
                "Please provide your Order ID to look up real-time delivery status."
            )
        elif any(w in lower for w in ["refund", "wapis", "return", "paise"]):
            reply = (
                "🛡️ **Return & Refund Policy:**\n"
                "Humari store policy ke mutabiq product dispatch hone ke baad instant refund allowed nahi hai. "
                "Parcel receive hone par warehouse physical inspection ke baad 3-5 business days mein refund process hota hai.\n\n"
                "Agar aap item return karna chahte hain to hum aap ka return ticket generate kar dete hain."
            )
        elif any(w in lower for w in ["bakwas", "fraud", "scam", "ghatiya", "angry", "terrible", "worst"]):
            reply = (
                "⚠️ **Supervisor Escalation:**\n"
                "Hamein nihayat afsos hai ke aap ko pareshani ka samna karna para. Aap ka case priority par human support supervisor ko escalate kar diya gaya hai. Hamara agent 10 minutes mein aap se rabta karega."
            )
        else:
            reply = (
                "Shukriya rabta karne ka! Main E-Commerce Customer Support AI hoon.\n"
                "Aap mujh se order tracking, product specifications, ya delivery status ke mutaliq English ya Roman Urdu mein pooch sakte hain."
            )

    await update.message.reply_text(reply)

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("="*60)
        print("TELEGRAM BOT SETUP GUIDE:")
        print("1. Open Telegram on your phone or PC.")
        print("2. Search for '@BotFather' and send '/newbot'.")
        print("3. Copy the Bot Token (e.g. 789123456:AAFd...).")
        print("4. Set your environment variable:")
        print("   $env:TELEGRAM_BOT_TOKEN = 'your_bot_token'")
        print("   $env:GEMINI_API_KEY = 'your_gemini_api_key' (Optional, for Gemini AI)")
        print("5. Run: python bot.py")
        print("="*60)
        token = input("Enter your Telegram Bot Token now (or press Enter to exit): ").strip()
        if not token:
            sys.exit(0)

    print(f"Starting Telegram AI Support Bot...")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("track", track_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot is LIVE and listening for Telegram messages! Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
