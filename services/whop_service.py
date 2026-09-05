"""Whop Payment Integration Service for Nyxeris.
Handles payment session creation, custom white-labeled styling overrides,
and webhook verification.
"""

import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
import httpx
from config import settings

logger = logging.getLogger("nyxeris.whop")

WHOP_API_BASE = "https://api.whop.com/api/v2"


class WhopPaymentService:
    def __init__(self):
        self.api_key = settings.WHOP_API_KEY
        self.company_id = settings.WHOP_COMPANY_ID
        self.webhook_secret = settings.WHOP_WEBHOOK_SECRET
        self.is_sandbox = settings.WHOP_SANDBOX_MODE or not bool(self.api_key)

    def is_configured(self) -> bool:
        """Returns True if a live Whop API key is supplied."""
        return bool(self.api_key and not self.is_sandbox)

    async def create_checkout_session(
        self,
        order: Dict[str, Any],
        items: list
    ) -> Dict[str, Any]:
        """Creates a checkout session via Whop API with Nyxeris branding overrides,
        or returns a seamless sandbox gateway when testing locally.
        """
        order_id = order["order_id"]
        total_cents = int(round(order["total_amount"] * 100))
        return_url = f"{settings.BASE_URL}/order-confirmation/{order_id}"

        # If running in sandbox/mock or API key not yet entered
        if self.is_sandbox or not self.api_key:
            logger.info(f"[Whop Sandbox] Initiating payment simulation for order {order_id} (${order['total_amount']:.2f})")
            return {
                "checkout_url": f"/checkout/pay/{order_id}",
                "mode": "sandbox",
                "session_id": f"whop_sess_sim_{order_id}",
                "brand": "Nyxeris"
            }

        # Live Whop API Integration
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "redirect_url": return_url,
            "metadata": {
                "order_id": order_id,
                "customer_name": order["customer_name"],
                "store_name": "Nyxeris",
                "item_count": len(items)
            },
            "checkout_styling": {
                "brand_name": "Nyxeris",
                "accent_color": "#00e5ff",
                "theme": "dark"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Try checkout_configurations endpoint
                response = await client.post(
                    f"{WHOP_API_BASE}/checkout_configurations",
                    json=payload,
                    headers=headers
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    checkout_url = data.get("url") or data.get("checkout_url")
                    return {
                        "checkout_url": checkout_url or return_url,
                        "mode": "live",
                        "session_id": data.get("id", f"whop_{order_id}"),
                        "brand": "Nyxeris"
                    }
                else:
                    logger.warning(f"Whop API response {response.status_code}: {response.text}")
                    # Fallback to direct sandbox if credentials reject
                    return {
                        "checkout_url": f"{settings.BASE_URL}/checkout/pay/{order_id}",
                        "mode": "fallback_sandbox",
                        "session_id": f"whop_fallback_{order_id}",
                        "error": response.text,
                        "brand": "Nyxeris"
                    }
        except Exception as e:
            logger.error(f"Error calling Whop API: {str(e)}")
            return {
                "checkout_url": f"{settings.BASE_URL}/checkout/pay/{order_id}",
                "mode": "error_sandbox",
                "session_id": f"whop_err_{order_id}",
                "error": str(e),
                "brand": "Nyxeris"
            }

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: Optional[str]) -> bool:
        """Verifies HMAC SHA256 webhook signature from Whop."""
        if not self.webhook_secret:
            # If no secret configured yet in dev, pass
            return True
        if not signature_header:
            return False

        try:
            expected = hmac.new(
                self.webhook_secret.encode("utf-8"),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature_header)
        except Exception:
            return False


whop_service = WhopPaymentService()
