"""
Core Application Configuration
Pydantic v2 Settings with environment variable support, project feature flags, and budget caps.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General App Settings
    APP_NAME: str = "Enterprise AI Automation Suite"
    APP_ENV: str = "development"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    SECRET_KEY: str = "production-ai-suite-secret-key-change-in-prod-xyz123"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500",
        "https://uzairio.web.app",
        "https://muhammaduzair-dev.web.app"
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./ai_systems.db"

    # AI Model Providers
    AI_PROVIDER: str = "gemini"  # "gemini" or "openai"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Public Demo Protection & Cost Controls
    GLOBAL_DAILY_BUDGET_USD: float = 10.00
    RATE_LIMIT_PER_MINUTE: int = 30
    RATE_LIMIT_BURST: int = 45
    SESSION_TTL_SECONDS: int = 3600  # 1 hour auto cleanup
    MAX_FILE_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB

    # Per-Project Feature Flags (True = active in API)
    FLAG_P01_REAL_ESTATE: bool = True
    FLAG_P02_LEGAL_RAG: bool = True
    FLAG_P03_SUPPORT_BOT: bool = True
    FLAG_P04_INVOICE_OCR: bool = True
    FLAG_P05_MONITOR: bool = True
    FLAG_P06_HR_RECRUITER: bool = True
    FLAG_P07_DENTAL_VOICE: bool = True
    FLAG_P08_COMPETITOR_INTEL: bool = True
    FLAG_P09_MEDIA_ENGINE: bool = True
    FLAG_P10_FIN_GUARD: bool = True

    # External Integration Flags
    SHOPIFY_SHOP_URL: Optional[str] = None
    SHOPIFY_ADMIN_ACCESS_TOKEN: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ALERT_CHAT_ID: Optional[str] = None
    QBO_CLIENT_ID: Optional[str] = None
    QBO_CLIENT_SECRET: Optional[str] = None
    QBO_REALM_ID: Optional[str] = None
    HUBSPOT_ACCESS_TOKEN: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

settings = Settings()
