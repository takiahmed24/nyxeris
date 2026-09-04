"""Programmatic Verification Script for CJ Dropshipping for Whop Bridge.
Tests database integrity, SKU resolution, order ingestion, CJ submission, and tracking sync.
"""

import sys
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import asyncio
from fastapi.testclient import TestClient
from main import app
from database import get_db_connection, init_db, get_settings
from services.sync_worker import process_incoming_whop_order, sync_all_pending_tracking

def test_pipeline():
    print("=" * 70)
    print(" [1/5] Testing Database Schema & Seed Data ...")
    init_db()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM sku_mappings")
    mapping_count = c.fetchone()[0]
    conn.close()
    print(f"       Found {mapping_count} SKU mappings in database.")
    assert mapping_count >= 1, "Expected seeded SKU mappings"

    print("=" * 70)
    print(" [2/5] Testing Whop Order Ingestion & CJ Sourcing Submission ...")
    test_whop_order = {
        "action": "payment.succeeded",
        "data": {
            "id": "WHOP-VERIFY-001",
            "total": 89.00,
            "currency": "usd",
            "customer": {
                "name": "Jordan Vance",
                "email": "jordan.vance@example.com",
                "phone": "+1 (555) 782-9901"
            },
            "shipping_address": {
                "line1": "100 Innovation Way",
                "city": "Austin",
                "state": "TX",
                "postal_code": "78701",
                "country": "United States",
                "country_code": "US"
            },
            "line_items": [
                {
                    "product_id": "prod_nyx_screenbar",
                    "product_title": "Nyxeris Horizon Pro ScreenBar Light",
                    "variant_title": "Standard",
                    "quantity": 2,
                    "unit_price": 89.00
                }
            ]
        }
    }

    # Run order ingestion asynchronously
    result = asyncio.run(process_incoming_whop_order(test_whop_order))
    print(f"       Order Ingestion Result: {result}")
    assert result.get("success") is True, f"Failed to ingest order: {result}"
    assert result.get("whop_order_id") == "WHOP-VERIFY-001"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE whop_order_id = 'WHOP-VERIFY-001'")
    order_row = dict(c.fetchone())
    conn.close()

    print(f"       Stored Order in DB: ID={order_row['whop_order_id']}, CJ_ID={order_row['cj_order_id']}, Status={order_row['cj_order_status']}")
    assert order_row["cj_order_id"] != "", "Expected CJ Order ID to be assigned"

    print("=" * 70)
    print(" [3/5] Testing Automated Carrier Tracking Sync ...")
    sync_res = asyncio.run(sync_all_pending_tracking())
    print(f"       Tracking Sync Result: {sync_res}")
    assert sync_res["updated"] >= 1, "Expected at least 1 order tracking record updated"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE whop_order_id = 'WHOP-VERIFY-001'")
    updated_order = dict(c.fetchone())
    conn.close()

    print(f"       Tracking Number: {updated_order['tracking_number']}")
    print(f"       Carrier: {updated_order['tracking_carrier']}")
    print(f"       Whop Fulfilled Status: {updated_order['whop_fulfilled']}")
    assert updated_order["whop_fulfilled"] == 1, "Expected order to be marked fulfilled for Whop"
    assert updated_order["tracking_number"] != "", "Expected carrier tracking number"

    print("=" * 70)
    print(" [4/5] Testing FastAPI Client Endpoints ...")
    client = TestClient(app)

    # Test Dashboard GET
    res_dash = client.get("/")
    assert res_dash.status_code == 200
    assert "CJ Fulfillment Bridge" in res_dash.text
    assert "WHOP-VERIFY-001" in res_dash.text
    print("       Dashboard GET '/' -> 200 OK")

    # Test SKU Mapping GET
    res_sku = client.get("/sku-mapping")
    assert res_sku.status_code == 200
    assert "Automated SKU Resolution" in res_sku.text
    print("       SKU Mapping GET '/sku-mapping' -> 200 OK")

    # Test Settings GET
    res_settings = client.get("/settings")
    assert res_settings.status_code == 200
    assert "CJ Dropshipping API 2.0" in res_settings.text
    print("       Settings GET '/settings' -> 200 OK")

    # Test Simulation API POST
    res_sim = client.post("/api/test/simulate-order")
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data.get("success") is True
    print(f"       Simulate Order POST '/api/test/simulate-order' -> 200 OK ({sim_data.get('whop_order_id')})")

    # Test Tracking Sync API POST
    res_sync_api = client.post("/api/sync/tracking")
    assert res_sync_api.status_code == 200
    print("       Tracking Sync POST '/api/sync/tracking' -> 200 OK")

    print("=" * 70)
    print(" [5/5] Checking Design Guidelines Compliance ...")
    css_path = BASE_DIR / "static" / "css" / "necyron_theme.css"
    assert css_path.exists(), "necyron_theme.css must exist"
    css_content = css_path.read_text(encoding="utf-8")
    assert "backdrop-filter" not in css_content, "STRICT REQUIREMENT VIOLATION: Found backdrop-filter (glassmorphism)"
    assert "#050E0E" in css_content, "Expected Necyron primary dark color token"
    assert "#243838" in css_content, "Expected Necyron solid border token"
    print("       VERIFIED: Zero glassmorphism detected. Pure Necyron tactical design tokens confirmed.")

    print("=" * 70)
    print(" ALL 5 VERIFICATION SUITES PASSED FLAWLESSLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_pipeline()
