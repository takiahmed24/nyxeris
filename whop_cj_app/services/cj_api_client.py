"""CJ Dropshipping Open API 2.0 Client.
Handles authentication, product queries, automated order submission, and tracking retrieval.
"""

import logging
import json
from typing import Dict, Any, List, Optional
import httpx
from config import settings
from database import get_settings, update_settings, log_event

logger = logging.getLogger("whop_cj.cj_api")

class CJApiClient:
    def __init__(self):
        self.base_url = settings.CJ_API_BASE

    def get_credentials(self, company_id: Optional[str] = None) -> Dict[str, Any]:
        """Loads live settings from database for specific company."""
        return get_settings(company_id)

    async def get_access_token(self, company_id: Optional[str] = None, force_refresh: bool = False) -> Optional[str]:
        """Fetches or refreshes the CJ Dropshipping Open API access token for a merchant."""
        creds = self.get_credentials(company_id)
        email = creds.get("cj_email")
        api_key = creds.get("cj_api_key")
        current_token = creds.get("cj_access_token")

        if not email or not api_key:
            logger.info(f"CJ Dropshipping credentials not configured for company {company_id or 'default'}. Operating in Sandbox mode.")
            return None

        if current_token and not force_refresh:
            return current_token

        # Request new access token from CJ API 2.0
        payload = {
            "email": email,
            "apiKey": api_key
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(f"{self.base_url}/authentication/getAccessToken", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("result") and "data" in data:
                        new_token = data["data"].get("accessToken")
                        expiry = data["data"].get("accessTokenExpiryDate", "")
                        
                        # Save in DB for this company
                        creds["cj_access_token"] = new_token
                        creds["cj_token_expiry"] = expiry
                        update_settings(creds, company_id=company_id)
                        log_event("cj_auth", "success", f"Refreshed CJ access token for company {company_id}", company_id=company_id or creds.get("company_id", "default"))
                        return new_token
                    else:
                        msg = data.get("message", "Unknown auth error from CJ API")
                        log_event("cj_auth", "error", f"CJ Auth Failed: {msg}", payload=data, company_id=company_id or "default")
                        return None
                else:
                    log_event("cj_auth", "error", f"CJ Auth HTTP {res.status_code}: {res.text}", company_id=company_id or "default")
                    return None
        except Exception as e:
            logger.error(f"Failed to communicate with CJ API: {e}")
            log_event("cj_auth", "error", f"Exception contacting CJ API: {str(e)}", company_id=company_id or "default")
            return None

    async def search_products(self, query: str, page: int = 1, size: int = 10) -> List[Dict[str, Any]]:
        """Searches CJ Dropshipping catalog for products and variants."""
        token = await self.get_access_token()
        if not token:
            # Fallback simulated products for testing/setup
            return [
                {
                    "pid": "CJ-DEMO-901",
                    "productName": f"CJ Sourced: {query.title()}",
                    "productSku": f"CJ-SKU-{hash(query) % 100000}",
                    "productImage": "https://img.cjdropshipping.com/demo.jpg",
                    "sellPrice": "14.50",
                    "variants": [
                        {"vid": "CJ-VAR-01", "variantSku": f"CJ-{query[:3].upper()}-STD", "variantName": "Standard Edition", "variantPrice": "14.50"},
                        {"vid": "CJ-VAR-02", "variantSku": f"CJ-{query[:3].upper()}-PRO", "variantName": "Pro Edition", "variantPrice": "19.99"}
                    ]
                }
            ]

        headers = {"CJ-Access-Token": token}
        params = {"productName": query, "pageNum": page, "pageSize": size}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{self.base_url}/product/list", headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("result"):
                        items = data.get("data", {}).get("list", [])
                        return items
            return []
        except Exception as e:
            logger.error(f"Error searching CJ products: {e}")
            return []

    async def create_fulfillment_order(
        self,
        order_number: str,
        shipping: Dict[str, Any],
        items: List[Dict[str, Any]],
        company_id: Optional[str] = None,
        note: str = "Fulfilled via Whop CJ SaaS Bridge"
    ) -> Dict[str, Any]:
        """Submits an order to CJ Dropshipping for fulfillment using merchant's credentials."""
        token = await self.get_access_token(company_id=company_id)

        # If in Sandbox / Local testing mode without live token:
        if not token:
            simulated_cj_id = f"CJ-{order_number.replace('NYX-', '').replace('WHOP-', '')}"
            logger.info(f"[Sandbox] Auto-simulating CJ Dropshipping order {simulated_cj_id} for {order_number} (Company: {company_id})")
            log_event("cj_order", "simulated", f"Simulated order {simulated_cj_id} for Whop order {order_number}", order_id=order_number, company_id=company_id or "default")
            return {
                "success": True,
                "mode": "sandbox",
                "cj_order_id": simulated_cj_id,
                "status": "CREATED",
                "message": "Order simulated successfully in sandbox."
            }

        headers = {
            "CJ-Access-Token": token,
            "Content-Type": "application/json"
        }

        # Format items according to CJ Open API 2.0 schema
        cj_products = []
        for itm in items:
            cj_products.append({
                "vid": itm.get("cj_variant_id") or itm.get("vid", ""),
                "quantity": int(itm.get("quantity", 1)),
                "unitPrice": float(itm.get("unit_price", 0.0))
            })

        payload = {
            "orderNumber": order_number,
            "shippingZip": shipping.get("postal_code", ""),
            "shippingCountryCode": shipping.get("country_code", "US"),
            "shippingCountry": shipping.get("country", "United States"),
            "shippingProvince": shipping.get("state", ""),
            "shippingCity": shipping.get("city", ""),
            "shippingAddress": shipping.get("address_line1", ""),
            "shippingAddress2": shipping.get("address_line2", ""),
            "shippingCustomerName": shipping.get("full_name", ""),
            "shippingPhone": shipping.get("phone", ""),
            "remark": note,
            "products": cj_products
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(
                    f"{self.base_url}/shopping/order/createOrder",
                    headers=headers,
                    json=payload
                )
                data = res.json() if res.status_code == 200 else {}
                if res.status_code == 200 and data.get("result"):
                    cj_order_id = data.get("data", "")
                    log_event("cj_order", "success", f"Created CJ Order: {cj_order_id}", order_id=order_number, payload=data, company_id=company_id or "default")
                    return {
                        "success": True,
                        "mode": "live",
                        "cj_order_id": cj_order_id,
                        "status": "SUBMITTED",
                        "raw": data
                    }
                else:
                    err_msg = data.get("message") or f"HTTP {res.status_code}: {res.text}"
                    log_event("cj_order", "error", f"CJ Order Creation failed: {err_msg}", order_id=order_number, payload=data, company_id=company_id or "default")
                    return {
                        "success": False,
                        "mode": "live",
                        "error": err_msg
                    }
        except Exception as e:
            logger.error(f"Error submitting order to CJ: {e}")
            log_event("cj_order", "error", f"Exception submitting order to CJ: {str(e)}", order_id=order_number, company_id=company_id or "default")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_order_tracking(self, cj_order_id: str, order_number: str, company_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries CJ for fulfillment and tracking status."""
        token = await self.get_access_token(company_id=company_id)

        if not token:
            # Deterministic simulation for sandbox
            return {
                "tracking_number": f"9400111899562{abs(hash(order_number)) % 10000000:07d}",
                "carrier": "USPS Priority",
                "tracking_url": f"https://t.17track.net/en#nums=9400111899562{abs(hash(order_number)) % 10000000:07d}",
                "status": "SHIPPED"
            }

        headers = {"CJ-Access-Token": token}
        params = {"orderId": cj_order_id}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{self.base_url}/shopping/order/getOrderDetail", headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("result") and "data" in data:
                        order_data = data["data"]
                        track_num = order_data.get("trackingNumber")
                        if track_num:
                            carrier = order_data.get("logisticName", "Standard Carrier")
                            return {
                                "tracking_number": track_num,
                                "carrier": carrier,
                                "tracking_url": f"https://t.17track.net/en#nums={track_num}",
                                "status": "SHIPPED" if order_data.get("orderStatus") in ("DELIVERED", "SHIPPED") else "PROCESSING"
                            }
            return None
        except Exception as e:
            logger.error(f"Error fetching CJ tracking for {cj_order_id}: {e}")
            return None

cj_client = CJApiClient()
