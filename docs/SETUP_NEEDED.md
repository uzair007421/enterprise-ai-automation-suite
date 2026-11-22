# External Services & Setup Guide (SETUP_NEEDED.md)

This document lists all external third-party services, sandboxes, and APIs utilized across the 10 AI automation projects.
Each adapter in the backend is designed to run in **Sandboxed Synthetic Mode** by default when credentials are unset, reporting `status: "not_configured"` truthfully through `/api/ai/<slug>/health`. To elevate any system to live external execution, supply the environment variable below in `backend/.env`.

---

## 1. Core AI Providers

| Service | Environment Variable | Free-Tier Link | Setup Instructions |
|---|---|---|---|
| **Google Gemini API** | `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | Create free API key. Rate limit: 15 RPM free tier. Model: `gemini-1.5-flash` or `gemini-2.0-flash`. |
| **OpenAI API** (Alternative) | `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com) | Create project API key. Models: `gpt-4o-mini`, `gpt-4o`. |

---

## 2. Per-Project Integrations

### Project 01: Real Estate Multi-Agent Sales
- **HubSpot CRM Adapter:**
  - `HUBSPOT_ACCESS_TOKEN`
  - Free Tier: [HubSpot Developer Account](https://developers.hubspot.com/) -> Create Private App -> Scopes: `crm.objects.contacts.write`, `crm.objects.deals.write`.
  - Fallback if unset: Local SQLite / JSON CRM Ledger with full idempotent upserts (`status: "sandbox"`).
- **Transactional Dispatch (Email/WhatsApp):**
  - `RESEND_API_KEY` / `SENDGRID_API_KEY` (Free: [Resend](https://resend.com) 100 emails/day)
  - `WHATSAPP_TOKEN` / `TELEGRAM_BOT_TOKEN`

### Project 03: Bilingual E-Commerce Support
- **Shopify Dev Store:**
  - `SHOPIFY_SHOP_URL` (e.g. `your-store.myshopify.com`)
  - `SHOPIFY_ADMIN_ACCESS_TOKEN`
  - Free Tier: [Shopify Partners](https://partners.shopify.com/) -> Create free development store -> Settings -> Apps -> Develop Apps -> Admin API scope: `read_orders`.
  - Fallback if unset: Verified local mock order repository with security verification checks.
- **Telegram Channel:**
  - `TELEGRAM_BOT_TOKEN` (Create via `@BotFather` on Telegram in 30 seconds).

### Project 04: Invoice Processing Pipeline
- **QuickBooks Online Sandbox:**
  - `QBO_CLIENT_ID`, `QBO_CLIENT_SECRET`, `QBO_REALM_ID`, `QBO_REFRESH_TOKEN`
  - Free Tier: [Intuit Developer](https://developer.intuit.com/) -> Create App -> Accounting Sandbox.
  - Fallback if unset: Local SQLite accounting ledger + formatted CSV Google Sheet export.

### Project 05: Self-Healing Workflow Monitor
- **Telegram Alert Dispatcher:**
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALERT_CHAT_ID`
- **n8n Instance:**
  - Self-hosted n8n in `infra/docker-compose.yml` or local desktop app.

### Project 06: HR AI Recruiter
- **Google Calendar API:**
  - `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
  - Free Tier: [Google Cloud Console](https://console.cloud.google.com/) -> Enable Google Calendar API.
  - Fallback if unset: Deterministic ICS calendar file generator + local calendar scheduling grid.

### Project 07: Dental Voice Appointment Agent
- **Vapi / Retell / WebRTC Voice Provider:**
  - `VAPI_API_KEY` / `RETELL_API_KEY`
  - Free Tier: [Vapi.ai](https://vapi.ai) ($10 free trial credit) / WebRTC browser audio stream.
- **Twilio SMS:**
  - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
  - Free Tier: [Twilio Console](https://console.twilio.com) (free trial with verified test phone numbers).

### Project 08: SaaS Competitor Intelligence
- **No Paid Accounts Needed.**
  - Uses public HTTP requests, Trafilatura clean text extraction, and project-hosted Chaos Competitor Sandbox.

### Project 09: Media Content Engine
- **Free Social Publishing Adapters:**
  - `TELEGRAM_CHANNEL_ID` / `BLUESKY_HANDLE` & `BLUESKY_APP_PASSWORD`
  - Free Tier: Bluesky app password generated in settings.

### Project 10: FinGuard Enterprise Agent Gate
- **No Paid Accounts Needed.**
  - Self-contained SQLite/Postgres financial database, HMAC/Ed25519 HMAC-secured signatures, and full SHA-256 audit chaining.
