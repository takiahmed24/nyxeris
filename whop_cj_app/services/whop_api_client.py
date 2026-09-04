"""Whop API Client and Webhook Handler for CJ Dropshipping SaaS Bridge."""

import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
import httpx
from config import settings
from database import get_settings, log_event

logger = logging.getLogger("whop_cj.whop_api")

class WhopApiClient:
    def __init__(self):
        self.base_url = settings.WHOP_API_BASE

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: Optional[str], company_id: Optional[str] = None) -> bool:
        """Verifies HMAC SHA256 signature from Whop for a specific merchant."""
        creds = get_settings(company_id)
        secret = creds.get("whop_webhook_secret") or settings.WHOP_WEBHOOK_SECRET
        
        # If secret is not set, allow for development/testing
        if not secret:
            return True

        if not signature_header:
            return False

        try:
            expected = hmac.new(
                secret.encode("utf-8"),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature_header)
        except Exception as e:
            logger.error(f"Error during webhook signature check: {e}")
            return False

    async def update_order_fulfillment(
        self,
        whop_order_id: str,
        tracking_number: str,
        carrier: str,
        tracking_url: str,
        company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pushes tracking number, carrier, and fulfillment status to Whop for a specific merchant."""
        creds = get_settings(company_id)
        api_key = creds.get("whop_api_key")

        if not api_key:
            logger.info(f"[Sandbox] Whop API key not set for {company_id or 'default'}. Simulating fulfillment update for {whop_order_id} ({tracking_number})")
            log_event(
                "whop_fulfill",
                "simulated",
                f"Simulated fulfillment for Whop order {whop_order_id} with tracking {tracking_number}",
                order_id=whop_order_id,
                payload={"tracking_number": tracking_number, "carrier": carrier, "tracking_url": tracking_url},
                company_id=company_id or "default"
            )
            return {
                "success": True,
                "mode": "sandbox",
                "message": "Whop order marked fulfilled (simulated)."
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "fulfillment_status": "fulfilled",
            "tracking_number": tracking_number,
            "carrier": carrier,
            "tracking_url": tracking_url
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    f"{self.base_url}/orders/{whop_order_id}/fulfill",
                    headers=headers,
                    json=payload
                )
                if res.status_code in (200, 201):
                    log_event("whop_fulfill", "success", f"Whop order {whop_order_id} fulfilled live", order_id=whop_order_id)
                    return {"success": True, "mode": "live"}
                else:
                    log_event("whop_fulfill", "error", f"Whop fulfill HTTP {res.status_code}: {res.text}", order_id=whop_order_id)
                    return {"success": False, "mode": "live", "error": res.text}
        except Exception as e:
            logger.error(f"Error calling Whop fulfillment API: {e}")
            log_event("whop_fulfill", "error", f"Exception fulfilling Whop order: {str(e)}", order_id=whop_order_id)
            return {"success": False, "error": str(e)}

whop_client = WhopApiClient()
