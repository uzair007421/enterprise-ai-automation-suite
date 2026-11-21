# 🛍️ Project 03: Bilingual WhatsApp E-Commerce AI Support with Escalation

> **Commercial Brief:**  
> *"We sell 200 products on Shopify. The bot must check live order status, handle returns, reply in English and Urdu, and hand over to a human if the customer is angry. It must never promise a refund by itself."*

---

## 🌟 Key Capabilities
* **Live Shopify Order Sync:** Real-time lookup of fulfillment tracking, couriers (TCS, Leopards, DHL), and delivery ETAs.
* **Bilingual English & Urdu NLP:** Seamlessly switches between English and Roman Urdu based on customer input.
* **Sentiment Detection & Hostility Escalation:** Instantly detects frustrated/angry customers, triggers a human takeover alert, and routes to a supervisor queue.
* **Strict Refund Guardrail:** Strictly prevents the AI from unauthorized monetary refunds. Instead, enforces the physical return policy and routes claims to the inspection team.

---

## 🏗️ Architecture & Guardrail Flow

```
                      [ WhatsApp Incoming Webhook ]
                                    │
                                    ▼
                      [ Language & Sentiment Analysis ]
                                    │
      ┌─────────────────────────────┼─────────────────────────────┐
      ▼                             ▼                             ▼
[ Sentiment < -0.4 ]      [ Refund Inquiry ]             [ Order Tracking ]
(Anger / Scam keywords)    (Money-back demand)            (SH-8821 Lookup)
      │                             │                             │
      ▼                             ▼                             ▼
[ TIER-2 HUMAN ESCALATION ] [ REFUND GUARDRAIL ]         [ SHOPIFY API QUERY ]
 • Alert Support Supervisor  • Block direct promise       • Live Courier Tracking
 • Comfort Customer          • Explain Return Steps       • Estimated Delivery
 • Handover Chat Session     • Require Physical Return    • Bilingual Status Reply
```

---

## ⚡ How to Run Live Interactive Demo

Zero external pip packages required. Runs completely using Python standard library:

```bash
cd 03-ecommerce-whatsapp-support
python run_demo.py
```
Open your browser at: **`http://localhost:8003`**

---

## 🎥 60-Second Fiverr Video Recording Script
1. **(0:00 - 0:15) The Hook:**  
   *"E-commerce brands lose up to 30% of repeat customers due to slow customer support and rigid bots that can't handle local languages or angry buyers. Here is our Shopify WhatsApp AI Support System."*
2. **(0:15 - 0:30) Live Order Tracking & Bilingual Test:**  
   Click the preset: *"AOA mera order SH-8821 kahan tak pohncha hai?"*  
   Show the bot replying in fluent Roman Urdu with live courier status, tracking number, and delivery time. Then test in English.
3. **(0:30 - 0:45) The Strict Refund Guardrail:**  
   Click: *"Refund my money right now!"*  
   Show the telemetry card: *"Notice the AI refuses to promise a financial payout by itself. It enforces the return policy safely."*
4. **(0:45 - 1:00) The Anger Escalation & Human Handover:**  
   Click: *"This is a SCAM and FRAUD! Connect to manager!"*  
   Show the instant red alert on the supervisor desk: *"The bot immediately halts automated replies and transfers the customer to a live human. Message me to set this up for your Shopify store!"*

---

## 💼 Fiverr Proposal Pitch Template

```text
Hi [Client Name],

I noticed you are looking for an intelligent WhatsApp AI Support bot for your Shopify store that can handle order tracking, returns, and bilingual conversations without risking rogue behavior.

I have already built an end-to-end WhatsApp E-Commerce Support bot featuring:
1. Live Shopify Order Lookup: Instant fulfillment, courier tracking, and estimated delivery dates.
2. English & Urdu Bilingual NLP: Automatic language detection and natural responses.
3. Sentiment-Driven Escalation: Automatic transfer to human agents whenever customer anger or hostility is detected.
4. Hard Refund Safeguard: The bot strictly adheres to your return policy and never issues unauthorized refunds.

I can integrate this with your Shopify store and WhatsApp Cloud API / Twilio in just 3 days. Let's start a quick chat so I can show you a live demo!
```

---

## 💰 Recommended Fiverr Gig Pricing
* **Basic ($200 - $350):** Single-language WhatsApp FAQ and order tracking bot.
* **Standard ($500 - $850):** Bilingual WhatsApp bot + Shopify Catalog sync + Return flow.
* **Premium ($1,200 - $2,000):** Full sentiment escalation + Human handover desk + Custom guardrails + Webhook alerts.
