"""CJ Dropshipping for Whop - Main FastAPI Application Server.
Provides tactical merchant dashboard, automated webhook receiver, SKU mapping, and tracking sync.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import settings
from database import get_db_connection, get_settings, update_settings, log_event, get_or_create_merchant, list_merchants, DEFAULT_COMPANY_ID
from services.sync_worker import process_incoming_whop_order, sync_all_pending_tracking
from services.whop_api_client import whop_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("whop_cj.main")

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Dedicated bridge connecting Whop payments directly to CJ Dropshipping fulfillment."
)

# Mount static files and local Necyron Google fonts
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/assets/fonts/google", StaticFiles(directory=str(BASE_DIR / "static" / "fonts")), name="fonts")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def get_request_company_id(request: Request) -> str:
    """Extracts tenant company_id from Whop iframe query parameters, cookies, or default."""
    cid = request.query_params.get("company_id")
    if not cid:
        cid = request.cookies.get("active_company_id")
    if not cid:
        cid = request.headers.get("x-company-id")
    if not cid or not cid.strip():
        cid = DEFAULT_COMPANY_ID
    return cid.strip()

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# HTML Web Dashboard Views (Multi-Tenant Isolated)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def view_dashboard(request: Request):
    """Main merchant dashboard showing metrics, pipeline stages, order feed, and logs."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    conn = get_db_connection()
    c = conn.cursor()

    # Calculate metrics scoped to this merchant
    c.execute("SELECT COUNT(*) FROM orders WHERE company_id = ?", (company_id,))
    total_orders = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE company_id = ? AND whop_fulfilled = 1", (company_id,))
    fulfilled_orders = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE company_id = ? AND whop_fulfilled = 0", (company_id,))
    pending_orders = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM sku_mappings WHERE company_id = ?", (company_id,))
    mapped_skus = c.fetchone()[0]

    # Fetch recent orders scoped to this merchant
    c.execute("SELECT * FROM orders WHERE company_id = ? ORDER BY id DESC LIMIT 50", (company_id,))
    order_rows = [dict(r) for r in c.fetchall()]

    for o in order_rows:
        try:
            items = json.loads(o["items_json"])
            o["items_summary"] = ", ".join([f"{it.get('quantity', 1)}x {it.get('whop_title', 'Product')}" for it in items])
        except Exception:
            o["items_summary"] = "Physical Goods"

    # Fetch recent logs scoped to this merchant
    c.execute("SELECT * FROM sync_logs WHERE company_id = ? ORDER BY id DESC LIMIT 20", (company_id,))
    log_rows = [dict(r) for r in c.fetchall()]

    conn.close()

    metrics = {
        "total_orders": total_orders,
        "fulfilled_orders": fulfilled_orders,
        "pending_orders": pending_orders,
        "mapped_skus": mapped_skus,
        "is_cj_connected": bool(current_merchant.get("cj_api_key"))
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "dashboard",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "metrics": metrics,
        "orders": order_rows,
        "logs": log_rows
    })

@app.get("/sku-mapping", response_class=HTMLResponse)
def view_sku_mapping(request: Request):
    """SKU resolution manager connecting merchant Whop items to CJ Dropshipping items."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sku_mappings WHERE company_id = ? ORDER BY id DESC", (company_id,))
    mappings = [dict(r) for r in c.fetchall()]
    conn.close()

    return templates.TemplateResponse("sku_mapping.html", {
        "request": request,
        "active_page": "sku_mapping",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "mappings": mappings
    })

@app.get("/settings", response_class=HTMLResponse)
def view_settings(request: Request):
    """Integration settings, credentials, and webhook endpoints for active merchant."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    host_header = request.headers.get("host", f"{settings.HOST}:{settings.PORT}")
    scheme = "https" if "https" in request.headers.get("x-forwarded-proto", "") else "http"
    webhook_url = f"{scheme}://{host_header}/api/webhooks/whop?company_id={company_id}"

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active_page": "settings",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "settings": current_merchant,
        "webhook_url": webhook_url
    })

# ---------------------------------------------------------------------------
# API Endpoints (Multi-Tenant Scoped)
# ---------------------------------------------------------------------------

@app.post("/api/webhooks/whop")
async def handle_whop_webhook(
    request: Request,
    whop_signature: Optional[str] = Header(None, alias="whop-signature")
):
    """Ingests incoming physical order webhooks from Whop with merchant routing."""
    raw_body = await request.body()

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Resolve company_id
    company_id = request.query_params.get("company_id")
    if not company_id:
        event_data = payload.get("data", payload)
        company_id = event_data.get("company_id") or payload.get("company_id")
        if not company_id and "metadata" in event_data:
            company_id = event_data["metadata"].get("company_id")
    if not company_id:
        company_id = DEFAULT_COMPANY_ID

    # Validate HMAC signature using this merchant's secret
    if not whop_client.verify_webhook_signature(raw_body, whop_signature, company_id=company_id):
        logger.warning(f"Invalid Whop webhook signature for company {company_id}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    action = payload.get("action") or payload.get("type", "unknown")
    logger.info(f"Received Whop Webhook event for company {company_id}: {action}")

    # Process successful payment events
    if action in ("payment.succeeded", "order.created", "checkout.completed", "test.event"):
        if "data" in payload and isinstance(payload["data"], dict):
            payload["data"]["company_id"] = company_id
        result = await process_incoming_whop_order(payload)
        return {"status": "processed", "company_id": company_id, "result": result}

    return {"status": "ignored", "action": action}

@app.post("/api/sync/tracking")
async def manual_sync_tracking(request: Request):
    """Triggers tracking sync for active merchant workspace."""
    company_id = get_request_company_id(request)
    res = await sync_all_pending_tracking(company_id=company_id)
    return res

class SkuMappingCreate(BaseModel):
    company_id: Optional[str] = None
    whop_product_id: str
    whop_product_title: str
    whop_variant_title: Optional[str] = "Standard"
    cj_variant_sku: str
    cj_product_title: str
    cj_estimated_cost: Optional[float] = 0.0

@app.post("/api/sku-mapping")
def create_sku_mapping(req: SkuMappingCreate, request: Request):
    """Creates or updates a merchant-specific SKU mapping."""
    company_id = req.company_id or get_request_company_id(request)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO sku_mappings (
            company_id, whop_product_id, whop_product_title, whop_variant_title,
            cj_product_id, cj_variant_sku, cj_product_title, cj_estimated_cost
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, whop_product_id, whop_variant_title) DO UPDATE SET
            whop_product_title = excluded.whop_product_title,
            cj_variant_sku = excluded.cj_variant_sku,
            cj_product_title = excluded.cj_product_title,
            cj_estimated_cost = excluded.cj_estimated_cost,
            updated_at = CURRENT_TIMESTAMP
    """, (
        company_id,
        req.whop_product_id,
        req.whop_product_title,
        req.whop_variant_title,
        f"CJ-PID-{hash(req.cj_variant_sku) % 10000}",
        req.cj_variant_sku,
        req.cj_product_title,
        req.cj_estimated_cost
    ))
    conn.commit()
    conn.close()
    return {"status": "saved", "company_id": company_id}

@app.delete("/api/sku-mapping/{mapping_id}")
def delete_sku_mapping(mapping_id: int):
    """Removes a SKU mapping."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sku_mappings WHERE id = ?", (mapping_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

class SettingsUpdate(BaseModel):
    company_id: Optional[str] = None
    account_name: Optional[str] = ""
    cj_email: Optional[str] = ""
    cj_api_key: Optional[str] = ""
    whop_api_key: Optional[str] = ""
    whop_webhook_secret: Optional[str] = ""
    auto_order_enabled: bool = True

@app.post("/api/settings")
def update_app_settings(req: SettingsUpdate, request: Request):
    """Updates settings and credentials for the specific merchant."""
    company_id = req.company_id or get_request_company_id(request)
    data = req.dict()
    update_settings(data, company_id=company_id)
    log_event("settings_update", "success", f"Merchant {company_id} updated credentials", company_id=company_id)
    return {"status": "updated", "company_id": company_id}

@app.post("/api/test/simulate-order")
async def simulate_test_order(request: Request):
    """Generates a realistic test physical order for the active merchant to verify pipeline."""
    import uuid
    import random

    company_id = get_request_company_id(request)
    test_id = f"WHOP-{company_id[:4].upper()}-{uuid.uuid4().hex[:6].upper()}"
    sample_cities = [("New York", "NY", "10001"), ("Austin", "TX", "78701"), ("Seattle", "WA", "98101")]
    city, state, zip_code = random.choice(sample_cities)

    mock_payload = {
        "action": "payment.succeeded",
        "company_id": company_id,
        "data": {
            "id": test_id,
            "company_id": company_id,
            "total": 89.00,
            "currency": "usd",
            "customer": {
                "name": "Alex Mercer",
                "email": "alex.mercer@example.com",
                "phone": "+1 (555) 349-1029"
            },
            "shipping_address": {
                "line1": "452 Hudson St, Apt 4B",
                "city": city,
                "state": state,
                "postal_code": zip_code,
                "country": "United States",
                "country_code": "US"
            },
            "line_items": [
                {
                    "product_id": "prod_nyx_screenbar",
                    "product_title": "Nyxeris Horizon Pro ScreenBar Light",
                    "variant_title": "Standard",
                    "quantity": 1,
                    "unit_price": 89.00
                }
            ]
        }
    }

    result = await process_incoming_whop_order(mock_payload)
    return result

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("       CJ DROPSHIPPING FOR WHOP - SAAS FULFILLMENT BRIDGE")
    print("=" * 70)
    print(f"[*] Starting Tactical Merchant Server at http://{settings.HOST}:{settings.PORT}")
    print("[*] Design: Solid Slate Tactical (Zero Glassmorphism - Necyron Theme)")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
