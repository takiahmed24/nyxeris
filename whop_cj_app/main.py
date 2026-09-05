"""CJ Dropshipping for Whop - Main FastAPI Application Server.
Provides tactical merchant dashboard, automated webhook receiver, SKU mapping, and tracking sync.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, Header, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import settings
from database import (
    get_db_connection, get_settings, update_settings, log_event,
    get_or_create_merchant, list_merchants, DEFAULT_COMPANY_ID, init_db,
    get_sourcing_requests, add_sourcing_request, get_notifications,
    mark_notifications_read, get_billing_transactions, add_billing_transaction,
    add_notification, update_billing_settings
)
from services.sync_worker import process_incoming_whop_order, sync_all_pending_tracking, list_cj_product_to_whop_service
from services.cj_api_client import cj_client
from services.whop_api_client import whop_client

# Ensure SQLite schema and tables are auto-initialized
init_db()

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
    """Extracts tenant company_id from Whop iframe query parameters, cookies, path, or default."""
    cid = request.path_params.get("company_id")
    if not cid:
        cid = request.query_params.get("company_id")
    if not cid:
        cid = request.cookies.get("active_company_id")
    if not cid:
        cid = request.headers.get("x-company-id")
    if not cid or not cid.strip():
        cid = DEFAULT_COMPANY_ID
    return cid.strip()

# ---------------------------------------------------------------------------
# HTML Web Dashboard Views (Multi-Tenant Isolated)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard/{company_id}", response_class=HTMLResponse)
@app.get("/experiences/{experience_id}", response_class=HTMLResponse)
def view_dashboard(request: Request, company_id: Optional[str] = None, experience_id: Optional[str] = None):
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

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
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

    return templates.TemplateResponse(request=request, name="sku_mapping.html", context={
        "request": request,
        "active_page": "sku_mapping",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "mappings": mappings
    })

@app.get("/products", response_class=HTMLResponse)
def view_products_catalog(request: Request):
    """Product catalog and listing manager pushing CJ items directly to Whop."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    return templates.TemplateResponse(request=request, name="products.html", context={
        "request": request,
        "active_page": "products",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants
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

    return templates.TemplateResponse(request=request, name="settings.html", context={
        "request": request,
        "active_page": "settings",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "settings": current_merchant,
        "webhook_url": webhook_url
    })

@app.get("/app-store", response_class=HTMLResponse)
@app.get("/listing", response_class=HTMLResponse)
@app.get("/discover", response_class=HTMLResponse)
def view_app_store_listing(request: Request):
    """Whop App Store marketplace listing page faithful to the CJ Dropshipping reference design."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    return templates.TemplateResponse(request=request, name="app_store.html", context={
        "request": request,
        "active_page": "app_store",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants
    })

@app.get("/privacy", response_class=HTMLResponse)
def view_privacy_policy(request: Request):
    """Public Privacy Policy required by Whop App Store Submission Guidelines."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    return templates.TemplateResponse(request=request, name="privacy.html", context={
        "request": request,
        "active_page": "privacy",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants
    })

@app.get("/terms", response_class=HTMLResponse)
def view_terms_of_service(request: Request):
    """Public Terms of Service required by Whop App Store Submission Guidelines."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    return templates.TemplateResponse(request=request, name="terms.html", context={
        "request": request,
        "active_page": "terms",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants
    })

@app.get("/orders", response_class=HTMLResponse)
@app.get("/orders/{order_id}", response_class=HTMLResponse)
def view_orders(request: Request, order_id: Optional[str] = None):
    """Orders management and real-time tracking timeline view (Screen 04)."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE company_id = ? ORDER BY id DESC", (company_id,))
    order_rows = [dict(r) for r in c.fetchall()]

    for o in order_rows:
        try:
            items = json.loads(o["items_json"])
            o["items_summary"] = ", ".join([f"{it.get('quantity', 1)}x {it.get('whop_title', 'Product')}" for it in items])
        except Exception:
            o["items_summary"] = "Physical Item"

    selected_order = None
    if order_id:
        selected_order = next((o for o in order_rows if order_id in o.get("whop_order_id", "")), None)
    if not selected_order and order_rows:
        selected_order = order_rows[0]

    conn.close()

    return templates.TemplateResponse(request=request, name="orders.html", context={
        "request": request,
        "active_page": "orders",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "orders": order_rows,
        "selected_order": selected_order
    })

@app.get("/sourcing", response_class=HTMLResponse)
def view_sourcing(request: Request):
    """Custom product sourcing request pipeline (Screen 07)."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()
    sourcing_requests = get_sourcing_requests(company_id)

    return templates.TemplateResponse(request=request, name="sourcing.html", context={
        "request": request,
        "active_page": "sourcing",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "sourcing_requests": sourcing_requests
    })

@app.get("/inventory", response_class=HTMLResponse)
def view_inventory(request: Request):
    """Inventory and Store Sync view (Screen 08)."""
    return view_sku_mapping(request)

@app.get("/analytics", response_class=HTMLResponse)
def view_analytics(request: Request):
    """Performance analytics, conversion rates, and revenue metrics (Screen 06)."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    return templates.TemplateResponse(request=request, name="analytics.html", context={
        "request": request,
        "active_page": "analytics",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants
    })

@app.get("/billing", response_class=HTMLResponse)
def view_billing(request: Request):
    """Plan management, fulfillment balance, payment methods, and invoices (Screen B)."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()
    transactions = get_billing_transactions(company_id)

    return templates.TemplateResponse(request=request, name="billing.html", context={
        "request": request,
        "active_page": "billing",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "transactions": transactions,
        "plan_tier": current_merchant.get("plan_tier") or "Creator",
        "plan_price": float(current_merchant.get("plan_price") or settings.PLAN_PRICE_USD),
        "plan_interval": current_merchant.get("plan_interval") or "monthly",
        "payment_method": current_merchant.get("payment_method") or "whop_balance",
        "whop_balance": float(current_merchant.get("whop_balance") or 432.00),
        "trial_days": settings.TRIAL_DAYS,
        "whop_checkout_url": settings.WHOP_CHECKOUT_URL,
        "whop_portal_url": settings.WHOP_PORTAL_URL
    })

@app.get("/shipping", response_class=HTMLResponse)
def view_shipping(request: Request):
    """Global shipping routes, express lines, and regional transit times (Screen 10)."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()

    return templates.TemplateResponse(request=request, name="shipping.html", context={
        "request": request,
        "active_page": "shipping",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants
    })

@app.get("/notifications", response_class=HTMLResponse)
def view_notifications(request: Request):
    """Full notifications activity feed (Screen 09)."""
    company_id = get_request_company_id(request)
    current_merchant = get_or_create_merchant(company_id)
    all_merchants = list_merchants()
    notifications = get_notifications(company_id)

    return templates.TemplateResponse(request=request, name="notifications.html", context={
        "request": request,
        "active_page": "notifications",
        "company_id": company_id,
        "current_merchant": current_merchant,
        "all_merchants": all_merchants,
        "notifications": notifications
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

@app.get("/api/cj/products")
async def api_get_cj_products(
    request: Request,
    tab: str = Query("my_products"),
    q: str = Query(""),
    page: int = Query(1),
    size: int = Query(20)
):
    """Fetches CJ products (either merchant's personal sourced items or catalog search) with Whop listing status."""
    company_id = get_request_company_id(request)

    if tab == "listed":
        # Load permanently saved products directly from local database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT 
                cj_product_id, whop_product_id, whop_product_title, cj_product_title,
                AVG(cj_estimated_cost) as sellPrice, COUNT(*) as variant_count
            FROM sku_mappings 
            WHERE company_id = ?
            GROUP BY whop_product_id
            ORDER BY id DESC
        """, (company_id,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()

        listed_products = []
        for r in rows:
            pid = r["cj_product_id"]
            detail = next((p for p in cj_client.SANDBOX_CATALOG if p["pid"] == pid), None)
            img = detail["productImage"] if detail else "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600"
            desc = detail["description"] if detail else "Direct dropshipped item listed on Whop store."
            listed_products.append({
                "pid": pid,
                "productName": r["whop_product_title"] or r["cj_product_title"],
                "productSku": f"SKU-{pid}",
                "sellPrice": float(r["sellPrice"] or 15.00),
                "productImage": img,
                "description": desc,
                "categoryName": "Active on Whop",
                "is_listed": True,
                "whop_product_id": r["whop_product_id"],
                "variants": [None] * int(r["variant_count"] or 1)
            })
        return {"products": listed_products, "tab": tab, "company_id": company_id}

    if tab == "catalog":
        products = await cj_client.search_products(query=q, page=page, size=size, company_id=company_id)
    else:
        products = await cj_client.get_my_products(keyword=q, page=page, size=size, company_id=company_id)

    # Check which products are already mapped/listed for this merchant
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT cj_product_id, whop_product_id, whop_product_title FROM sku_mappings WHERE company_id = ?", (company_id,))
    mapped_rows = c.fetchall()
    conn.close()

    mapped_lookup = {}
    for row in mapped_rows:
        mapped_lookup[row["cj_product_id"]] = {
            "whop_product_id": row["whop_product_id"],
            "whop_product_title": row["whop_product_title"]
        }

    enriched = []
    for p in products:
        p_dict = dict(p)
        pid = p_dict.get("pid")
        is_mapped = pid in mapped_lookup
        p_dict["is_listed"] = is_mapped
        if is_mapped:
            p_dict["whop_product_id"] = mapped_lookup[pid]["whop_product_id"]
        enriched.append(p_dict)

    return {"products": enriched, "tab": tab, "company_id": company_id}

class ListProductRequest(BaseModel):
    cj_pid: str
    selling_price: float
    custom_title: Optional[str] = None
    custom_description: Optional[str] = None
    company_id: Optional[str] = None

@app.post("/api/whop/list-product")
async def api_list_product_to_whop(req: ListProductRequest, request: Request):
    """Directly creates a product and plan on Whop and saves SKU mappings for automated fulfillment."""
    company_id = req.company_id or get_request_company_id(request)
    result = await list_cj_product_to_whop_service(
        company_id=company_id,
        cj_pid=req.cj_pid,
        selling_price=req.selling_price,
        custom_title=req.custom_title,
        custom_description=req.custom_description
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Listing to Whop failed"))
    return result

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

class SourcingCreateRequest(BaseModel):
    company_id: Optional[str] = None
    product_name: str
    target_price: float
    image_url: Optional[str] = ""
    details: Optional[str] = ""

@app.post("/api/sourcing/request")
def api_submit_sourcing_request(req: SourcingCreateRequest, request: Request):
    """Submits a new custom sourcing request to the database."""
    company_id = req.company_id or get_request_company_id(request)
    req_id = add_sourcing_request(
        company_id=company_id,
        product_name=req.product_name,
        target_price=req.target_price,
        image_url=req.image_url or "",
        details=req.details or ""
    )
    log_event("sourcing_request", "success", f"Submitted sourcing request for {req.product_name}", company_id=company_id)
    return {"status": "submitted", "id": req_id, "company_id": company_id}

@app.post("/api/notifications/read")
def api_mark_notifications_read_endpoint(request: Request):
    """Marks all notifications as read for current merchant."""
    company_id = get_request_company_id(request)
    mark_notifications_read(company_id)
    return {"status": "marked_read", "company_id": company_id}

class BillingMethodUpdate(BaseModel):
    company_id: Optional[str] = None
    payment_method: str  # 'whop_balance' or 'credit_card'

@app.post("/api/billing/switch-payment-method")
def api_switch_payment_method(req: BillingMethodUpdate, request: Request):
    """Allows merchant to toggle their default billing source between Whop Balance and Credit Card."""
    company_id = req.company_id or get_request_company_id(request)
    method = "whop_balance" if "balance" in req.payment_method.lower() else "credit_card"
    update_billing_settings(company_id=company_id, payment_method=method)
    label = "Whop Merchant Balance" if method == "whop_balance" else "Credit Card (Visa •••• 4242)"
    add_notification(
        company_id, "system", "Payment Preference Updated",
        f"Default subscription payment source set to {label}.", "Just now"
    )
    log_event("billing_method_switch", "success", f"Merchant {company_id} switched payment method to {method}", company_id=company_id)
    return {"status": "updated", "payment_method": method, "label": label}

class PayPlanBalanceRequest(BaseModel):
    company_id: Optional[str] = None
    plan_tier: Optional[str] = "Creator"
    amount: Optional[float] = 5.00
    interval: Optional[str] = "monthly"

@app.post("/api/billing/pay-with-whop-balance")
def api_pay_with_whop_balance(req: PayPlanBalanceRequest, request: Request):
    """Deducts subscription fee directly from merchant's accrued Whop Balance and issues receipt."""
    import uuid
    company_id = req.company_id or get_request_company_id(request)
    merchant = get_or_create_merchant(company_id)
    current_bal = float(merchant.get("whop_balance") or 432.00)
    amount = float(req.amount or 5.00)

    if current_bal < amount:
        raise HTTPException(status_code=400, detail=f"Insufficient Whop Balance (${current_bal:.2f}). Please pay with Credit Card or top up.")

    ref_id = f"WHOP-BAL-{uuid.uuid4().hex[:8].upper()}"
    desc = f"{req.plan_tier} Plan Subscription ({req.interval.capitalize()}) - Paid via Whop Balance"

    # Deduct balance & save transaction
    update_billing_settings(
        company_id=company_id,
        plan_tier=req.plan_tier,
        plan_price=amount,
        plan_interval=req.interval,
        payment_method="whop_balance",
        balance_delta=-amount
    )
    add_billing_transaction(company_id, "subscription", -amount, desc, ref_id=ref_id)
    add_notification(
        company_id, "system", "Plan Payment Successful",
        f"${amount:.2f} deducted from Whop Balance for {req.plan_tier} Plan. Reference: {ref_id}", "Just now"
    )
    log_event("billing_payment", "success", f"Processed ${amount:.2f} subscription payment via Whop Balance for {company_id}", company_id=company_id)

    return {
        "status": "success",
        "message": f"Successfully paid ${amount:.2f} using Whop Balance. Receipt: {ref_id}",
        "ref_id": ref_id,
        "new_balance": current_bal - amount
    }

class UpgradePlanRequest(BaseModel):
    company_id: Optional[str] = None
    plan_tier: str  # 'Starter', 'Creator', 'Pro'
    interval: Optional[str] = "monthly"
    payment_method: Optional[str] = "whop_balance"  # 'whop_balance' or 'whop_checkout'

@app.post("/api/billing/upgrade-plan")
def api_upgrade_plan(req: UpgradePlanRequest, request: Request):
    """Changes merchant plan subscription and initiates payment via Whop Balance or Whop Checkout."""
    import uuid
    company_id = req.company_id or get_request_company_id(request)
    tier = req.plan_tier.capitalize()
    interval = req.interval.lower()

    # Pricing lookup
    if tier == "Starter":
        price = 0.0
    elif tier == "Creator":
        price = 48.00 if interval == "yearly" else 5.00
    elif tier == "Pro":
        price = 279.00 if interval == "yearly" else 29.00
    else:
        price = 5.00

    if req.payment_method == "whop_checkout":
        return {
            "status": "redirect",
            "checkout_url": f"{settings.WHOP_CHECKOUT_URL}?plan={tier.lower()}&interval={interval}&company_id={company_id}",
            "message": f"Redirecting to Whop Checkout for {tier} plan..."
        }

    # Whop Balance Payment
    merchant = get_or_create_merchant(company_id)
    current_bal = float(merchant.get("whop_balance") or 432.00)

    if price > 0 and current_bal < price:
        return {
            "status": "redirect",
            "checkout_url": f"{settings.WHOP_CHECKOUT_URL}?plan={tier.lower()}&company_id={company_id}",
            "message": f"Whop balance insufficient (${current_bal:.2f}). Redirecting to Whop Checkout..."
        }

    ref_id = f"WHOP-UPG-{uuid.uuid4().hex[:8].upper()}"
    desc = f"Upgraded to {tier} Plan ({interval.capitalize()}) - Paid via Whop Balance"

    update_billing_settings(
        company_id=company_id,
        plan_tier=tier,
        plan_price=price,
        plan_interval=interval,
        payment_method="whop_balance",
        balance_delta=-price if price > 0 else 0.0
    )
    if price > 0:
        add_billing_transaction(company_id, "subscription", -price, desc, ref_id=ref_id)

    add_notification(
        company_id, "system", f"Subscribed to {tier} Plan",
        f"Your store is now on the {tier} Plan (${price:.2f}/{interval}). Paid via Whop Balance.", "Just now"
    )
    log_event("plan_upgrade", "success", f"Merchant {company_id} upgraded to {tier} ({interval}) via Whop Balance", company_id=company_id)

    return {
        "status": "success",
        "plan_tier": tier,
        "plan_price": price,
        "interval": interval,
        "message": f"Successfully activated {tier} Plan! Charged ${price:.2f} to Whop Balance.",
        "ref_id": ref_id
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("       CJ DROPSHIPPING FOR WHOP - SAAS FULFILLMENT BRIDGE")
    print("=" * 70)
    print(f"[*] Starting Tactical Merchant Server at http://{settings.HOST}:{settings.PORT}")
    print("[*] Design: Solid Slate Tactical (Zero Glassmorphism - Necyron Theme)")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
