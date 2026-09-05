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

    # Mock Sandbox Catalog for Development and Initial Setup
    SANDBOX_CATALOG = [
        {
            "pid": "CJ-PID-WATCH-01",
            "productName": "Minimalist Mechanical Automatic Watch",
            "productSku": "CJ-SKU-WATCH-BASE",
            "productImage": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=80",
            "sellPrice": "24.50",
            "description": "Crafted from 316L surgical-grade stainless steel with sapphire crystal glass and automatic mechanical movement. Water resistant to 50M.",
            "categoryName": "Watches & Jewelry",
            "variants": [
                {"vid": "CJ-VAR-WATCH-01", "variantSku": "CJ-WATCH-SLV", "variantName": "Silver Mesh / 40mm", "variantPrice": "24.50", "variantImage": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400"},
                {"vid": "CJ-VAR-WATCH-02", "variantSku": "CJ-WATCH-BLK", "variantName": "Matte Obsidian / 40mm", "variantPrice": "26.50", "variantImage": "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=400"},
                {"vid": "CJ-VAR-WATCH-03", "variantSku": "CJ-WATCH-RSG", "variantName": "Rose Gold / Leather", "variantPrice": "28.00", "variantImage": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400"}
            ]
        },
        {
            "pid": "CJ-PID-HOODIE-02",
            "productName": "Heavyweight 450GSM Oversized Hoodie",
            "productSku": "CJ-SKU-HOOD-BASE",
            "productImage": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600&auto=format&fit=crop&q=80",
            "sellPrice": "18.20",
            "description": "Pre-shrunk 100% organic cotton fleece with double-needle ribbed binding, drop-shoulder silhouette, and hidden kangaroo pocket.",
            "categoryName": "Apparel",
            "variants": [
                {"vid": "CJ-VAR-HOOD-01", "variantSku": "CJ-HOOD-BLK-L", "variantName": "Pitch Black - Large", "variantPrice": "18.20", "variantImage": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400"},
                {"vid": "CJ-VAR-HOOD-02", "variantSku": "CJ-HOOD-BLK-XL", "variantName": "Pitch Black - XL", "variantPrice": "18.20", "variantImage": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400"},
                {"vid": "CJ-VAR-HOOD-03", "variantSku": "CJ-HOOD-GRY-L", "variantName": "Heather Gray - Large", "variantPrice": "18.20", "variantImage": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=400"}
            ]
        },
        {
            "pid": "CJ-PID-GLASSES-03",
            "productName": "Titanium Polarized UV400 Aviator Sunglasses",
            "productSku": "CJ-SKU-AV-BASE",
            "productImage": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=600&auto=format&fit=crop&q=80",
            "sellPrice": "11.80",
            "description": "Ultra-light aerospace titanium frame, anti-glare TAC polarized lenses with 100% UVA/UVB protection and spring hinges.",
            "categoryName": "Accessories",
            "variants": [
                {"vid": "CJ-VAR-AV-01", "variantSku": "CJ-AV-GUN", "variantName": "Gunmetal / Deep Smoke", "variantPrice": "11.80", "variantImage": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400"},
                {"vid": "CJ-VAR-AV-02", "variantSku": "CJ-AV-GLD", "variantName": "Brushed Gold / Amber", "variantPrice": "12.50", "variantImage": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=400"}
            ]
        },
        {
            "pid": "CJ-PID-EARBUDS-04",
            "productName": "Active Noise-Cancelling True Wireless Earbuds",
            "productSku": "CJ-SKU-ANC-BASE",
            "productImage": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80",
            "sellPrice": "16.50",
            "description": "Hybrid active noise cancellation (-35dB), Bluetooth 5.3 low-latency mode, 32-hour total battery life with wireless charging case.",
            "categoryName": "Consumer Electronics",
            "variants": [
                {"vid": "CJ-VAR-ANC-01", "variantSku": "CJ-ANC-BLK", "variantName": "Phantom Black", "variantPrice": "16.50", "variantImage": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400"},
                {"vid": "CJ-VAR-ANC-02", "variantSku": "CJ-ANC-WHT", "variantName": "Glacier White", "variantPrice": "16.50", "variantImage": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400"}
            ]
        },
        {
            "pid": "CJ-PID-BAG-05",
            "productName": "Weatherproof Cordura Modular Sling Bag",
            "productSku": "CJ-SKU-SLING-BASE",
            "productImage": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",
            "sellPrice": "13.90",
            "description": "Indestructible 500D Cordura ballistic nylon with YKK Aquaguard zippers, magnetic Fidlock buckle, and padded tablet compartment.",
            "categoryName": "Bags & Luggage",
            "variants": [
                {"vid": "CJ-VAR-SLING-01", "variantSku": "CJ-SLING-BLK", "variantName": "Stealth Black", "variantPrice": "13.90", "variantImage": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400"},
                {"vid": "CJ-VAR-SLING-02", "variantSku": "CJ-SLING-OLV", "variantName": "Ranger Olive", "variantPrice": "13.90", "variantImage": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400"}
            ]
        }
    ]

    async def get_my_products(
        self,
        keyword: str = "",
        page: int = 1,
        size: int = 20,
        company_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Queries products the merchant has sourced or saved in their personal CJ account."""
        token = await self.get_access_token(company_id=company_id)
        if not token:
            # Return matching sandbox catalog items for offline testing
            results = self.SANDBOX_CATALOG
            if keyword:
                kw = keyword.lower()
                results = [p for p in results if kw in p["productName"].lower() or kw in p["productSku"].lower() or kw in p.get("categoryName", "").lower()]
            return results

        headers = {"CJ-Access-Token": token}
        params = {"pageNum": page, "pageSize": size}
        if keyword:
            params["keyword"] = keyword

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{self.base_url}/product/myProduct/query", headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("result"):
                        items = data.get("data", {}).get("list", [])
                        if items:
                            return items
                # Fallback to general list if myProduct returned empty
                return await self.search_products(keyword, page, size, company_id=company_id)
        except Exception as e:
            logger.error(f"Error fetching my CJ products: {e}")
            return [p for p in self.SANDBOX_CATALOG if not keyword or keyword.lower() in p["productName"].lower()]

    async def search_products(
        self,
        query: str = "",
        page: int = 1,
        size: int = 20,
        company_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Searches CJ Dropshipping catalog for products and variants."""
        token = await self.get_access_token(company_id=company_id)
        if not token:
            # Fallback simulated products for testing/setup
            results = self.SANDBOX_CATALOG
            if query:
                q = query.lower()
                results = [p for p in results if q in p["productName"].lower() or q in p["productSku"].lower() or q in p.get("categoryName", "").lower()]
            return results

        headers = {"CJ-Access-Token": token}
        params = {"productName": query, "pageNum": page, "pageSize": size}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{self.base_url}/product/list", headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("result"):
                        items = data.get("data", {}).get("list", [])
                        if items:
                            return items
            return [p for p in self.SANDBOX_CATALOG if not query or query.lower() in p["productName"].lower()]
        except Exception as e:
            logger.error(f"Error searching CJ products: {e}")
            return [p for p in self.SANDBOX_CATALOG if not query or query.lower() in p["productName"].lower()]

    async def get_product_detail(
        self,
        pid: str,
        company_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Queries full details, gallery images, and variant list for a specific CJ Product ID."""
        token = await self.get_access_token(company_id=company_id)

        # Check sandbox catalog first
        for p in self.SANDBOX_CATALOG:
            if p["pid"] == pid:
                return p

        if not token:
            return None

        headers = {"CJ-Access-Token": token}
        params = {"pid": pid}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(f"{self.base_url}/product/query", headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("result") and "data" in data:
                        return data["data"]
            return None
        except Exception as e:
            logger.error(f"Error fetching product detail for {pid}: {e}")
            return None

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
