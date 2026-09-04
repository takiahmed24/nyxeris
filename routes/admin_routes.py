"""Admin Cockpit API routes for Nyxeris.
Provides physical product fulfillment tracking, dropshipping carrier assignment,
inventory controls, and Whop white-labeling configuration.
"""

import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from config import settings
from database import get_db_connection

router = APIRouter(prefix="/api/admin", tags=["Admin Cockpit"])


class FulfillmentUpdateSchema(BaseModel):
    fulfillment_status: str  # unfulfilled, processing, shipped, delivered, cancelled
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    notes: Optional[str] = None


class ProductSaveSchema(BaseModel):
    id: Optional[str] = None
    title: str
    slug: str
    description: str
    category: str
    price: float
    compare_at_price: Optional[float] = None
    cost_price: Optional[float] = None
    stock_quantity: int
    sku: str
    supplier_url: Optional[str] = None
    image_url: str
    badge: Optional[str] = None
    specs: Optional[dict] = None
    variants: Optional[list] = None


class SettingsUpdateSchema(BaseModel):
    whop_api_key: Optional[str] = None
    whop_company_id: Optional[str] = None
    whop_webhook_secret: Optional[str] = None
    whop_sandbox_mode: Optional[bool] = None
    store_name: Optional[str] = None
    store_support_email: Optional[str] = None
    free_shipping_threshold: Optional[float] = None


@router.get("/stats")
def get_admin_dashboard_stats():
    """Calculates high-level revenue and fulfillment stats."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM orders WHERE payment_status = 'paid'")
    paid_count, total_revenue = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM orders WHERE fulfillment_status = 'unfulfilled' AND payment_status = 'paid'")
    pending_fulfillment = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products WHERE stock_quantity <= 10")
    low_stock_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]

    conn.close()

    return {
        "total_revenue": round(total_revenue, 2),
        "paid_orders_count": paid_count,
        "pending_fulfillment_count": pending_fulfillment,
        "low_stock_count": low_stock_count,
        "total_products": total_products,
        "whop_status": "Live Connected" if settings.WHOP_API_KEY and not settings.WHOP_SANDBOX_MODE else "Sandbox / Dev Mode"
    }


@router.get("/orders")
def list_admin_orders(
    fulfillment: Optional[str] = None,
    payment: Optional[str] = None
):
    """Lists customer orders with item details and dropshipping status."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if fulfillment and fulfillment != "all":
        query += " AND fulfillment_status = ?"
        params.append(fulfillment)

    if payment and payment != "all":
        query += " AND payment_status = ?"
        params.append(payment)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    order_rows = cursor.fetchall()

    orders_list = []
    for r in order_rows:
        order = dict(r)
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order["order_id"],))
        order["items"] = [dict(it) for it in cursor.fetchall()]
        orders_list.append(order)

    conn.close()
    return orders_list


@router.post("/orders/{order_id}/fulfillment")
def update_order_fulfillment(order_id: str, data: FulfillmentUpdateSchema):
    """Updates dropshipping fulfillment, carrier, and tracking number."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    cursor.execute("""
        UPDATE orders
        SET fulfillment_status = ?,
            carrier = ?,
            tracking_number = ?,
            tracking_url = ?,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE order_id = ?
    """, (
        data.fulfillment_status,
        data.carrier,
        data.tracking_number,
        data.tracking_url,
        data.notes,
        order_id
    ))
    conn.commit()

    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    updated = dict(cursor.fetchone())
    conn.close()
    return {"status": "success", "order": updated}


@router.post("/products")
def save_product(data: ProductSaveSchema):
    """Creates or updates a physical product."""
    conn = get_db_connection()
    cursor = conn.cursor()

    product_id = data.id or f"prod_{data.slug.replace('-', '_')[:16]}"
    specs_json = json.dumps(data.specs or {})
    variants_json = json.dumps(data.variants or [])

    cursor.execute("""
        INSERT INTO products (
            id, title, slug, description, category, price, compare_at_price,
            cost_price, stock_quantity, sku, supplier_url, image_url, badge,
            specs, variants
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            slug = excluded.slug,
            description = excluded.description,
            category = excluded.category,
            price = excluded.price,
            compare_at_price = excluded.compare_at_price,
            cost_price = excluded.cost_price,
            stock_quantity = excluded.stock_quantity,
            sku = excluded.sku,
            supplier_url = excluded.supplier_url,
            image_url = excluded.image_url,
            badge = excluded.badge,
            specs = excluded.specs,
            variants = excluded.variants
    """, (
        product_id, data.title, data.slug, data.description, data.category,
        data.price, data.compare_at_price, data.cost_price, data.stock_quantity,
        data.sku, data.supplier_url, data.image_url, data.badge,
        specs_json, variants_json
    ))
    conn.commit()
    conn.close()
    return {"status": "success", "product_id": product_id}


@router.delete("/products/{product_id}")
def delete_product(product_id: str):
    """Removes a product from catalog."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "product_id": product_id}


@router.get("/settings")
def get_store_settings():
    """Returns current Whop and store configurations."""
    return {
        "store_name": settings.STORE_NAME,
        "store_tagline": settings.STORE_TAGLINE,
        "store_support_email": settings.STORE_SUPPORT_EMAIL,
        "currency": settings.STORE_CURRENCY,
        "free_shipping_threshold": settings.FREE_SHIPPING_THRESHOLD,
        "default_shipping_fee": settings.DEFAULT_SHIPPING_FEE,
        "whop_api_key_configured": bool(settings.WHOP_API_KEY),
        "whop_company_id": settings.WHOP_COMPANY_ID,
        "whop_sandbox_mode": settings.WHOP_SANDBOX_MODE,
        "webhook_url": f"{settings.BASE_URL}/api/webhooks/whop",
        "whop_branding_checklist": {
            "business_name": "Set to 'Nyxeris' in Whop Company Settings",
            "statement_descriptor": "Set to 'NYXERIS' so bank statements read 'NYXERIS*STORE'",
            "checkout_styling": "Primary color #00e5ff, theme 'dark', Nyxeris logo uploaded",
            "customer_emails": "Handled natively by Nyxeris Receipt Engine with 0 Whop branding"
        }
    }


# ==============================================================================
# TITAN-ONE LEARNING & WORKFLOW AUTOMATION ROUTES
# ==============================================================================

class TeachSkillSchema(BaseModel):
    skill_name: str
    description: str
    steps: List[str]
    category: Optional[str] = "Custom Automation"
    trigger_keywords: Optional[List[str]] = None


@router.get("/titan/skills")
def get_titan_skills():
    """Returns all learned automation skills in Titan's library."""
    from services.titan_learning_engine import titan_engine
    return {"skills": titan_engine.get_skills_list()}


@router.post("/titan/teach")
def teach_titan_skill(data: TeachSkillSchema):
    """Teaches Titan-One a new repeating workflow, validates comprehension, and saves to library."""
    from services.titan_learning_engine import titan_engine
    new_skill = titan_engine.teach_new_skill(
        skill_name=data.skill_name,
        description=data.description,
        steps=data.steps,
        category=data.category or "Custom Automation",
        trigger_keywords=data.trigger_keywords
    )
    return {"status": "success", "skill": new_skill}


@router.post("/titan/run/{skill_id}")
def run_titan_skill(skill_id: str):
    """Executes a learned skill automatically."""
    from services.titan_learning_engine import titan_engine
    result = titan_engine.execute_skill(skill_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/titan/logs")
def get_titan_training_logs():
    """Returns real-time Titan reasoning and training logs."""
    from services.titan_learning_engine import titan_engine
    return {"logs": titan_engine.get_training_logs()}

