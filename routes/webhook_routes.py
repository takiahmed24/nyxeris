"""Whop Webhook Ingestion Router for Nyxeris.
Listens for successful Whop payments, transitions physical orders to 'paid',
decrements inventory, and generates Nyxeris white-labeled receipts.
"""

import json
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional

from database import get_db_connection
from services.whop_service import whop_service
from services.receipt_service import generate_nyxeris_receipt_pdf

logger = logging.getLogger("nyxeris.webhooks")
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/whop")
async def handle_whop_webhook(
    request: Request,
    whop_signature: Optional[str] = Header(None, alias="whop-signature")
):
    """Processes incoming payment webhooks from Whop."""
    raw_body = await request.body()

    # Validate HMAC signature
    if not whop_service.verify_webhook_signature(raw_body, whop_signature):
        logger.warning("Invalid Whop webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = data.get("action") or data.get("type", "unknown")
    event_data = data.get("data", {})
    logger.info(f"Received Whop Webhook event: {action}")

    # Identify order_id from metadata
    metadata = event_data.get("metadata", {})
    order_id = metadata.get("order_id")

    # Fallback to custom fields or checkout ID
    if not order_id and "custom_fields" in event_data:
        order_id = event_data["custom_fields"].get("order_id")

    if not order_id:
        # Check if payment_id matches any existing record
        payment_id = event_data.get("id")
        logger.warning(f"Webhook missing order_id in metadata, payment_id: {payment_id}")
        return {"status": "ignored", "reason": "No order_id in metadata"}

    # Process successful payment events
    if action in ("payment.succeeded", "payment.created", "checkout.completed", "test.event"):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        order_row = cursor.fetchone()

        if not order_row:
            conn.close()
            logger.warning(f"Order {order_id} from webhook not found in Nyxeris database")
            return {"status": "not_found", "order_id": order_id}

        order = dict(order_row)

        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        items = [dict(r) for r in cursor.fetchall()]

        # If not yet marked as paid, update status and deduct stock
        if order.get("payment_status") != "paid":
            cursor.execute("""
                UPDATE orders
                SET payment_status = 'paid',
                    whop_payment_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
            """, (event_data.get("id", "whop_webhook_verified"), order_id))

            for itm in items:
                cursor.execute(
                    "UPDATE products SET stock_quantity = MAX(0, stock_quantity - ?) WHERE id = ?",
                    (itm["quantity"], itm["product_id"])
                )

            conn.commit()

        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        updated_order = dict(cursor.fetchone())
        conn.close()

        # Generate official Nyxeris PDF receipt
        pdf_path = generate_nyxeris_receipt_pdf(updated_order, items)
        logger.info(f"Generated Nyxeris PDF receipt for {order_id} at {pdf_path}")

        return {
            "status": "processed",
            "order_id": order_id,
            "payment_status": "paid",
            "receipt_generated": True
        }

    return {"status": "ignored", "action": action}
