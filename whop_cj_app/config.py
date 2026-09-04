"""Configuration settings for CJ Dropshipping for Whop SaaS Bridge."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "bridge.db"

class Settings:
    # Server configuration
    APP_NAME: str = "CJ Dropshipping for Whop"
    APP_VERSION: str = "1.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8090
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = str(DB_PATH)

    # Whop Developer Platform
    WHOP_API_BASE: str = "https://api.whop.com/api/v2"
    WHOP_APP_ID: str = os.getenv("WHOP_APP_ID", "")
    WHOP_CLIENT_SECRET: str = os.getenv("WHOP_CLIENT_SECRET", "")
    WHOP_WEBHOOK_SECRET: str = os.getenv("WHOP_WEBHOOK_SECRET", "")
    
    # Pricing Configuration
    PLAN_NAME: str = "CJ Dropshipping Automation"
    PLAN_PRICE_USD: float = 5.00
    TRIAL_DAYS: int = 60

    # CJ Dropshipping Open API 2.0
    CJ_API_BASE: str = "https://developers.cjdropshipping.com/api2.0/v1"
    CJ_EMAIL: str = os.getenv("CJ_EMAIL", "")
    CJ_API_KEY: str = os.getenv("CJ_API_KEY", "")
    CJ_ACCESS_TOKEN: str = os.getenv("CJ_ACCESS_TOKEN", "")

    # Polling & Worker Settings
    TRACKING_POLL_INTERVAL_MINUTES: int = 30
    AUTO_CONFIRM_ORDERS: bool = False  # If True, automatically debits CJ balance

settings = Settings()
