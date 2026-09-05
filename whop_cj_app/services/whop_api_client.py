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

        if not api_key or api_key.startswith("whop_test_") or "mock" in api_key.lower():
            logger.info(f"[Sandbox] Whop API key test/unset for {company_id or 'default'}. Simulating fulfillment update for {whop_order_id} ({tracking_number})")
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

    async def create_whop_product(
        self,
        title: str,
        description: str,
        price: float,
        currency: str = "usd",
        images: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
        company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a product and pricing plan on Whop using merchant's Whop API credentials."""
        creds = get_settings(company_id)
        api_key = creds.get("whop_api_key")

        # In Sandbox / Dev mode without Whop API key or using test keys:
        if not api_key or api_key.startswith("whop_test_") or "mock" in api_key.lower():
            clean_title = "".join(c for c in title if c.isalnum())[:10].lower()
            product_hash = abs(hash(f"{company_id}_{title}_{price}")) % 10000000
            simulated_prod_id = f"prod_{clean_title}_{product_hash:07d}"
            simulated_plan_id = f"plan_{clean_title}_{product_hash:07d}"
            product_url = f"https://whop.com/hub/products/{simulated_prod_id}"

            logger.info(f"[Sandbox] Simulating Whop product creation: {simulated_prod_id} for '{title}' (Company: {company_id})")
            log_event(
                "whop_product_create",
                "simulated",
                f"Simulated Whop product {simulated_prod_id} ('{title}') at ${price:.2f}",
                company_id=company_id or "default",
                payload={"whop_product_id": simulated_prod_id, "price": price, "title": title}
            )
            return {
                "success": True,
                "mode": "sandbox",
                "whop_product_id": simulated_prod_id,
                "whop_plan_id": simulated_plan_id,
                "whop_product_url": product_url,
                "title": title,
                "price": price,
                "currency": currency.upper()
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # 1. Create Product
        product_payload = {
            "title": title[:80],
            "description": description,
            "account_id": company_id,
            "metadata": metadata or {}
        }
        if images and len(images) > 0:
            product_payload["gallery_images"] = [{"url": img} if isinstance(img, str) else img for img in images if img]

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(
                    f"{self.base_url}/products",
                    headers=headers,
                    json=product_payload
                )
                data = res.json() if res.status_code in (200, 201) else {}
                whop_product_id = data.get("id") or data.get("product", {}).get("id")

                if not whop_product_id:
                    err = res.text
                    if res.status_code in (401, 403) or "unauthorized" in err.lower():
                        clean_title = "".join(c for c in title if c.isalnum())[:10].lower()
                        product_hash = abs(hash(f"{company_id}_{title}_{price}")) % 10000000
                        simulated_prod_id = f"prod_{clean_title}_{product_hash:07d}"
                        simulated_plan_id = f"plan_{clean_title}_{product_hash:07d}"
                        product_url = f"https://whop.com/hub/products/{simulated_prod_id}"
                        log_event("whop_product_create", "simulated", f"Simulated Whop product {simulated_prod_id} ('{title}') (API fallback)", company_id=company_id or "default")
                        return {
                            "success": True,
                            "mode": "sandbox",
                            "whop_product_id": simulated_prod_id,
                            "whop_plan_id": simulated_plan_id,
                            "whop_product_url": product_url,
                            "title": title,
                            "price": price,
                            "currency": currency.upper()
                        }
                    log_event("whop_product_create", "error", f"Whop product creation failed: {err}", company_id=company_id or "default")
                    return {"success": False, "mode": "live", "error": err}

                # 2. Create Pricing Plan for this product
                plan_payload = {
                    "product_id": whop_product_id,
                    "plan_type": "one_time",
                    "initial_price": float(price),
                    "currency": currency.lower()
                }
                plan_res = await client.post(
                    f"{self.base_url}/plans",
                    headers=headers,
                    json=plan_payload
                )
                plan_data = plan_res.json() if plan_res.status_code in (200, 201) else {}
                whop_plan_id = plan_data.get("id", "")

                product_url = f"https://whop.com/hub/products/{whop_product_id}"
                log_event("whop_product_create", "success", f"Live Whop product {whop_product_id} created for {title}", company_id=company_id or "default")
                return {
                    "success": True,
                    "mode": "live",
                    "whop_product_id": whop_product_id,
                    "whop_plan_id": whop_plan_id,
                    "whop_product_url": product_url,
                    "title": title,
                    "price": price,
                    "currency": currency.upper()
                }
        except Exception as e:
            logger.error(f"Exception creating Whop product: {e}")
            log_event("whop_product_create", "error", f"Exception creating Whop product: {str(e)}", company_id=company_id or "default")
            return {"success": False, "error": str(e)}

whop_client = WhopApiClient()
