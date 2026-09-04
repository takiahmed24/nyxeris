"""Configuration settings for Nyxeris Storefront & Whop Payment Integration."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RECEIPTS_DIR = DATA_DIR / "receipts"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    # Store Branding
    STORE_NAME: str = "Nyxeris"
    STORE_TAGLINE: str = "Your Needs, We Stock Up — Precision Hardware & Desk Architecture"
    STORE_SUPPORT_EMAIL: str = os.getenv("STORE_SUPPORT_EMAIL", "ahmedmuhammadtaki@gmail.com")
    STORE_OWNER_EMAIL: str = os.getenv("STORE_OWNER_EMAIL", "ahmedmuhammadtaki@gmail.com")
    STORE_CURRENCY: str = "USD"
    STORE_CURRENCY_SYMBOL: str = "$"
    BASE_URL: str = "http://localhost:8000"

    # Whop Payment Integration
    # Leave WHOP_API_KEY empty to automatically operate in Sandbox / Seamless Dev Mode
    WHOP_API_KEY: str = os.getenv("WHOP_API_KEY", "")
    WHOP_COMPANY_ID: str = os.getenv("WHOP_COMPANY_ID", "")
    WHOP_WEBHOOK_SECRET: str = os.getenv("WHOP_WEBHOOK_SECRET", "")
    WHOP_SANDBOX_MODE: bool = os.getenv("WHOP_SANDBOX_MODE", "true").lower() in ("true", "1", "yes")

    # Shipping & Tax (Location-Tiered Rates for Real CJ Logistics)
    DEFAULT_SHIPPING_FEE: float = 14.99
    SHIPPING_RATES: dict = {
        "us_ca": 14.99,  # United States & Canada
        "uk_eu": 16.99,  # United Kingdom & Europe
        "row": 19.99     # Australia, New Zealand & Rest of World
    }
    FREE_SHIPPING_THRESHOLD: float = 150.00
    TAX_RATE: float = 0.08  # 8% estimated sales tax
    PREMIUM_PACKAGING_FEE: float = 2.99  # Nyxeris Signature Luxury Gift Box add-on

    def get_shipping_fee(self, country: str = "United States", subtotal: float = 0.0) -> float:
        if subtotal >= self.FREE_SHIPPING_THRESHOLD:
            return 0.0
        c = (country or "").strip().lower()
        if any(term in c for term in ["united states", "usa", "us", "canada", "ca"]):
            return self.SHIPPING_RATES.get("us_ca", 14.99)
        elif any(term in c for term in ["united kingdom", "uk", "great britain", "england", "scotland", "germany", "france", "italy", "spain", "netherlands", "belgium", "sweden", "norway", "denmark", "finland", "poland", "austria", "switzerland", "portugal", "ireland", "europe"]):
            return self.SHIPPING_RATES.get("uk_eu", 16.99)
        else:
            return self.SHIPPING_RATES.get("row", 19.99)

    # Database
    DATABASE_PATH: str = str(DATA_DIR / "nyxeris.db")

    # Admin access
    ADMIN_PIN: str = os.getenv("ADMIN_PIN", "1337")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
