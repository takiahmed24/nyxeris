"""Automated Sync Worker for CJ Dropshipping for Whop SaaS Bridge.
Orchestrates order resolution, CJ fulfillment creation, and tracking polling back to Whop.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from database import get_db_connection, log_event, get_settings
from services.cj_api_client import cj_client
from services.whop_api_client import whop_client

logger = logging.getLogger("whop_cj.worker")

async def process_incoming_whop_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Processes a new paid Whop physical order, resolves SKUs, and submits to CJ Dropshipping."""
    event_data = payload.get("data", payload)
    
    # 1. Extract Whop Order identifiers & Multi-tenant Company ID
    company_id = event_data.get("company_id") or payload.get("company_id")
    if not company_id and "metadata" in event_data:
        company_id = event_data["metadata"].get("company_id")
    if not company_id:
        from database import DEFAULT_COMPANY_ID
        company_id = DEFAULT_COMPANY_ID

    whop_order_id = event_data.get("id") or event_data.get("order_id")
    if not whop_order_id and "metadata" in event_data:
        whop_order_id = event_data["metadata"].get("order_id")

    if not whop_order_id:
        msg = "Missing order ID in incoming Whop payload"
        logger.warning(msg)
        log_event("order_receive", "error", msg, payload=payload, company_id=company_id)
        return {"success": False, "error": msg}

    # 2. Extract Customer & Shipping Information
    customer = event_data.get("customer") or {}
    customer_name = customer.get("name") or event_data.get("customer_name") or "Whop Customer"
    customer_email = customer.get("email") or event_data.get("customer_email") or ""
    customer_phone = customer.get("phone") or event_data.get("customer_phone") or ""

    shipping = event_data.get("shipping_address") or event_data.get("address") or {}
    if not shipping and "metadata" in event_data:
        shipping = event_data["metadata"].get("shipping", {})

    shipping_normalized = {
        "full_name": customer_name,
        "email": customer_email,
        "phone": customer_phone or shipping.get("phone", ""),
        "address_line1": shipping.get("line1") or shipping.get("address_line1", "123 Main St"),
        "address_line2": shipping.get("line2") or shipping.get("address_line2", ""),
        "city": shipping.get("city", "Los Angeles"),
        "state": shipping.get("state") or shipping.get("province", "CA"),
        "postal_code": shipping.get("postal_code") or shipping.get("zip", "90001"),
        "country": shipping.get("country", "United States"),
        "country_code": shipping.get("country_code", "US")
    }

    # 3. Extract line items
    raw_items = event_data.get("line_items") or event_data.get("items") or []
    if not raw_items and "metadata" in event_data:
        raw_items = event_data["metadata"].get("items", [])

    if not raw_items:
        product = event_data.get("product", {})
        raw_items = [{
            "product_id": product.get("id", "whop_prod_default"),
            "product_title": product.get("name", "Whop Physical Product"),
            "variant_title": "Standard",
            "quantity": 1,
            "unit_price": float(event_data.get("total", 0.0))
        }]

    total_amount = float(event_data.get("total") or event_data.get("total_amount") or 0.0)
    currency = event_data.get("currency", "USD").upper()

    # 4. Resolve items against Company's SKU Mappings
    conn = get_db_connection()
    c = conn.cursor()

    resolved_items = []
    has_unmapped = False

    for item in raw_items:
        prod_id = str(item.get("product_id", ""))
        var_title = item.get("variant_title", "Standard")
        qty = int(item.get("quantity", 1))
        price = float(item.get("unit_price", 0.0))

        # Check sku_mappings table for this merchant company
        c.execute("""
            SELECT * FROM sku_mappings 
            WHERE company_id = ? AND (whop_product_id = ? OR whop_variant_title = ?)
            LIMIT 1
        """, (company_id, prod_id, var_title))
        mapping = c.fetchone()

        if mapping:
            mapping_dict = dict(mapping)
            resolved_items.append({
                "whop_product_id": prod_id,
                "whop_title": item.get("product_title") or mapping_dict["whop_product_title"],
                "cj_product_id": mapping_dict["cj_product_id"],
                "cj_variant_id": mapping_dict["cj_variant_id"],
                "cj_variant_sku": mapping_dict["cj_variant_sku"],
                "quantity": qty,
                "unit_price": price
            })
        else:
            has_unmapped = True
            resolved_items.append({
                "whop_product_id": prod_id,
                "whop_title": item.get("product_title", "Unmapped Product"),
                "cj_product_id": "UNMAPPED",
                "cj_variant_id": "",
                "cj_variant_sku": "UNMAPPED-SKU",
                "quantity": qty,
                "unit_price": price
            })

    # 5. Save or update order in local database scoped to company
    c.execute("""
        INSERT INTO orders (
            company_id, whop_order_id, customer_name, customer_email, customer_phone,
            shipping_country, shipping_address_json, items_json,
            total_amount, currency, whop_payment_status, cj_order_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'paid', ?)
        ON CONFLICT(whop_order_id) DO UPDATE SET
            shipping_address_json = excluded.shipping_address_json,
            items_json = excluded.items_json,
            updated_at = CURRENT_TIMESTAMP
    """, (
        company_id,
        whop_order_id,
        customer_name,
        customer_email,
        customer_phone,
        shipping_normalized["country"],
        json.dumps(shipping_normalized),
        json.dumps(resolved_items),
        total_amount,
        currency,
        "UNMAPPED_SKU" if has_unmapped else "PENDING_CREATION"
    ))
    conn.commit()
    conn.close()

    log_event("order_receive", "success", f"Ingested order {whop_order_id} ({len(resolved_items)} items) for company {company_id}", order_id=whop_order_id, company_id=company_id)

    # 6. If ready and auto-orders enabled for this merchant, place order with CJ Dropshipping
    settings_data = get_settings(company_id)
    if settings_data.get("auto_order_enabled", 1) and not has_unmapped:
        cj_result = await cj_client.create_fulfillment_order(
            order_number=whop_order_id,
            shipping=shipping_normalized,
            items=resolved_items,
            company_id=company_id
        )
        if cj_result.get("success"):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE orders 
                SET cj_order_id = ?, cj_order_status = 'SUBMITTED', updated_at = CURRENT_TIMESTAMP
                WHERE whop_order_id = ?
            """, (cj_result.get("cj_order_id", ""), whop_order_id))
            conn.commit()
            conn.close()
            return {"success": True, "whop_order_id": whop_order_id, "cj_order_id": cj_result.get("cj_order_id")}
        else:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE orders 
                SET last_error = ?, cj_order_status = 'CREATION_FAILED', updated_at = CURRENT_TIMESTAMP
                WHERE whop_order_id = ?
            """, (cj_result.get("error", "Unknown error"), whop_order_id))
            conn.commit()
            conn.close()
            return {"success": False, "error": cj_result.get("error")}

    return {
        "success": True,
        "whop_order_id": whop_order_id,
        "status": "UNMAPPED_SKU" if has_unmapped else "SAVED"
    }

async def sync_all_pending_tracking(company_id: Optional[str] = None) -> Dict[str, Any]:
    """Scans pending CJ orders, checks for carrier tracking numbers, and pushes to Whop."""
    conn = get_db_connection()
    c = conn.cursor()
    if company_id:
        c.execute("""
            SELECT * FROM orders 
            WHERE company_id = ? AND cj_order_id != '' AND whop_fulfilled = 0
        """, (company_id,))
    else:
        c.execute("""
            SELECT * FROM orders 
            WHERE cj_order_id != '' AND whop_fulfilled = 0
        """)
    orders_to_check = [dict(r) for r in c.fetchall()]
    conn.close()

    updated_count = 0
    for order in orders_to_check:
        whop_order_id = order["whop_order_id"]
        cj_order_id = order["cj_order_id"]
        order_cid = order.get("company_id", company_id or "biz_ea3gy6pg50A7px")

        tracking = await cj_client.get_order_tracking(cj_order_id, whop_order_id, company_id=order_cid)
        if tracking and tracking.get("tracking_number"):
            track_num = tracking["tracking_number"]
            carrier = tracking.get("carrier", "Standard Carrier")
            track_url = tracking.get("tracking_url", f"https://t.17track.net/en#nums={track_num}")

            # Push tracking to Whop for this specific merchant
            whop_res = await whop_client.update_order_fulfillment(
                whop_order_id=whop_order_id,
                tracking_number=track_num,
                carrier=carrier,
                tracking_url=track_url,
                company_id=order_cid
            )

            # Update local database
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE orders
                SET tracking_number = ?,
                    tracking_carrier = ?,
                    tracking_url = ?,
                    whop_fulfilled = 1,
                    cj_order_status = 'SHIPPED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE whop_order_id = ?
            """, (track_num, carrier, track_url, whop_order_id))
            conn.commit()
            conn.close()

            updated_count += 1
            log_event(
                "tracking_synced",
                "success",
                f"Synced tracking {track_num} ({carrier}) to Whop for {whop_order_id}",
                order_id=whop_order_id,
                company_id=order_cid
            )

    return {"checked": len(orders_to_check), "updated": updated_count}
