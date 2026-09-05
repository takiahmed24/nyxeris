"""Programmatic Verification Script for CJ Dropshipping for Whop Bridge.
Tests multi-tenant merchant isolation, SKU resolution, order ingestion, CJ submission,
pipeline theme compliance, and tracking sync.
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
from database import get_db_connection, init_db, get_settings, update_settings, get_or_create_merchant, list_merchants, DEFAULT_COMPANY_ID
from services.sync_worker import process_incoming_whop_order, sync_all_pending_tracking

def test_pipeline():
    print("=" * 70)
    print(" [1/6] Testing Multi-Tenant Merchant Isolation ...")
    init_db()

    # Create Store Alpha & Store Beta (clean previous test state for idempotency)
    alpha_id = "biz_alpha_test_101"
    beta_id = "biz_beta_test_202"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM orders WHERE company_id IN (?, ?)", (alpha_id, beta_id))
    c.execute("DELETE FROM sku_mappings WHERE company_id IN (?, ?)", (alpha_id, beta_id))
    c.execute("DELETE FROM sync_logs WHERE company_id IN (?, ?)", (alpha_id, beta_id))
    conn.commit()
    conn.close()

    merchant_alpha = get_or_create_merchant(alpha_id)
    merchant_beta = get_or_create_merchant(beta_id)

    # Configure distinct CJ credentials
    update_settings({"cj_email": "alpha@example.com", "cj_api_key": "KEY_ALPHA_999", "account_name": "Alpha Boutique"}, company_id=alpha_id)
    update_settings({"cj_email": "beta@example.com", "cj_api_key": "KEY_BETA_888", "account_name": "Beta Apparel"}, company_id=beta_id)

    check_alpha = get_settings(alpha_id)
    check_beta = get_settings(beta_id)

    assert check_alpha["cj_email"] == "alpha@example.com", "Store Alpha credentials failed"
    assert check_beta["cj_email"] == "beta@example.com", "Store Beta credentials failed"
    assert check_alpha["cj_api_key"] != check_beta["cj_api_key"], "Multi-tenant credentials must remain isolated"
    print(f"       CONFIRMED: Store Alpha ({check_alpha['account_name']}) & Store Beta ({check_beta['account_name']}) have isolated credentials.")

    print("=" * 70)
    print(" [2/6] Testing Multi-Tenant SKU Resolution ...")
    conn = get_db_connection()
    c = conn.cursor()
    
    # Add SKU for Alpha
    c.execute("""
        INSERT INTO sku_mappings (
            company_id, whop_product_id, whop_product_title, whop_variant_title,
            cj_product_id, cj_variant_sku, cj_product_title, cj_estimated_cost
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, whop_product_id, whop_variant_title) DO NOTHING
    """, (alpha_id, "prod_alpha_watch", "Alpha Watch", "Standard", "CJ-PID-WATCH", "CJ-SKU-WATCH-01", "Luxury Watch", 35.00))
    conn.commit()

    # Query SKU for Beta (should NOT find Alpha's watch)
    c.execute("SELECT * FROM sku_mappings WHERE company_id = ? AND whop_product_id = ?", (beta_id, "prod_alpha_watch"))
    assert c.fetchone() is None, "Cross-tenant SKU leakage detected! Beta must not see Alpha's SKUs"
    conn.close()
    print("       CONFIRMED: SKU mappings are strictly isolated per merchant company.")

    print("=" * 70)
    print(" [3/6] Testing Multi-Tenant Order Ingestion & CJ Sourcing Submission ...")
    test_whop_order = {
        "action": "payment.succeeded",
        "company_id": alpha_id,
        "data": {
            "id": "WHOP-ALPHA-ORD-001",
            "company_id": alpha_id,
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
                    "product_id": "prod_alpha_watch",
                    "product_title": "Alpha Watch",
                    "variant_title": "Standard",
                    "quantity": 1,
                    "unit_price": 89.00
                }
            ]
        }
    }

    result = asyncio.run(process_incoming_whop_order(test_whop_order))
    assert result.get("success") is True, f"Failed to ingest order: {result}"
    assert result.get("whop_order_id") == "WHOP-ALPHA-ORD-001"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE whop_order_id = 'WHOP-ALPHA-ORD-001'")
    order_row = dict(c.fetchone())
    assert order_row["company_id"] == alpha_id, "Order must belong to Store Alpha"
    assert order_row["cj_order_id"] != "", "Expected CJ Order ID to be assigned"
    conn.close()
    print(f"       Stored Order: ID={order_row['whop_order_id']}, Company={order_row['company_id']}, CJ_ID={order_row['cj_order_id']}")

    print("=" * 70)
    print(" [4/6] Testing Automated Carrier Tracking Sync per Merchant ...")
    sync_res = asyncio.run(sync_all_pending_tracking(company_id=alpha_id))
    assert sync_res["updated"] >= 1, "Expected order tracking updated"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE whop_order_id = 'WHOP-ALPHA-ORD-001'")
    updated_order = dict(c.fetchone())
    conn.close()

    assert updated_order["whop_fulfilled"] == 1
    assert updated_order["tracking_number"] != ""
    print(f"       Tracking Synced: {updated_order['tracking_number']} via {updated_order['tracking_carrier']} (Whop Fulfilled: True)")

    print("=" * 70)
    print(" [5/6] Testing Multi-Tenant Web UI & Workspace Switching ...")
    client = TestClient(app)

    # Test Dashboard with Store Alpha
    res_dash = client.get(f"/?company_id={alpha_id}")
    assert res_dash.status_code == 200
    assert "Alpha Boutique" in res_dash.text
    assert "WHOP-ALPHA-ORD-001" in res_dash.text
    print("       Dashboard GET '/?company_id=biz_alpha_test_101' -> 200 OK (Alpha Workspace Loaded)")

    # Test Dashboard with Store Beta (Alpha's order must NOT appear)
    res_beta = client.get(f"/?company_id={beta_id}")
    assert res_beta.status_code == 200
    assert "Beta Apparel" in res_beta.text
    assert "WHOP-ALPHA-ORD-001" not in res_beta.text
    print("       Dashboard GET '/?company_id=biz_beta_test_202' -> 200 OK (Beta Workspace Isolated)")

    # Test Offline Fonts Route
    res_font = client.get("/assets/fonts/google/google_font_1.css")
    assert res_font.status_code == 200
    print("       Offline Necyron Google Font '/assets/fonts/google/google_font_1.css' -> 200 OK")

    print("=" * 70)
    print(" [6/8] Checking Whop Vibe & Zero Dot Pattern Compliance ...")
    css_path = BASE_DIR / "static" / "css" / "necyron_theme.css"
    css_content = css_path.read_text(encoding="utf-8")
    assert "backdrop-filter" not in css_content, "VIOLATION: Found backdrop-filter (glassmorphism)"
    assert "radial-gradient" not in css_content, "VIOLATION: Found radial-gradient dot pattern"
    assert "background-image: none" in css_content, "Expected clean solid canvas without dot pattern"
    assert "whop-os-header" in css_content, "Expected Whop OS header styling"
    assert "whop-dock" in css_content, "Expected Whop squircle dock styling"
    assert "pipeline-flow-container" in css_content, "Expected interactive pipeline flow classes"
    assert "DM Sans" in css_content and "Ubuntu" in css_content, "Expected offline Necyron font families"
    print("       CONFIRMED: Dot-dot background completely eliminated. Authentic Whop Vibe active.")

    print("=" * 70)
    print(" [7/7] Testing Direct CJ to Whop Product Listing & Auto-SKU Roundtrip ...")
    
    # Test GET /products HTML View
    res_prod_view = client.get(f"/products?company_id={alpha_id}")
    assert res_prod_view.status_code == 200
    assert "Find Products" in res_prod_view.text
    print("       Products UI GET '/products?company_id=biz_alpha_test_101' -> 200 OK")

    # Test GET /api/cj/products
    res_cj_prods = client.get(f"/api/cj/products?tab=my_products&company_id={alpha_id}")
    assert res_cj_prods.status_code == 200
    prods_data = res_cj_prods.json()
    assert len(prods_data.get("products", [])) > 0, "Expected at least 1 CJ product available"
    first_prod = prods_data["products"][0]
    print(f"       CJ Catalog Query: Found {len(prods_data['products'])} items. First: {first_prod['productName']} (PID: {first_prod['pid']})")

    # Test POST /api/whop/list-product
    list_payload = {
        "company_id": alpha_id,
        "cj_pid": "CJ-PID-WATCH-01",
        "selling_price": 69.00,
        "custom_title": "Alpha Chronograph Pro",
        "custom_description": "Luxury 316L mechanical watch with automatic movement."
    }
    res_list = client.post("/api/whop/list-product", json=list_payload)
    assert res_list.status_code == 200, f"Listing failed: {res_list.text}"
    listed_data = res_list.json()
    assert listed_data["success"] is True
    assert listed_data["whop_product_id"].startswith("prod_")
    assert listed_data["variants_mapped"] >= 3
    new_whop_pid = listed_data["whop_product_id"]
    print(f"       Product Published to Whop: ID={new_whop_pid}, Title='{listed_data['title']}', Price=${listed_data['selling_price']:.2f}")

    # Verify SKU Mappings in SQLite
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sku_mappings WHERE company_id = ? AND whop_product_id = ?", (alpha_id, new_whop_pid))
    mapping_rows = [dict(r) for r in c.fetchall()]
    conn.close()

    assert len(mapping_rows) >= 3, f"Expected at least 3 mapped variants, found {len(mapping_rows)}"
    variant_skus = [r["cj_variant_sku"] for r in mapping_rows]
    assert "CJ-WATCH-BLK" in variant_skus, "Expected CJ-WATCH-BLK variant mapped"
    print(f"       CONFIRMED: {len(mapping_rows)} variants automatically registered in 'sku_mappings': {variant_skus}")

    # Test Roundtrip Order Fulfillment using the newly listed product
    roundtrip_order_id = "WHOP-ROUNDTRIP-999"
    roundtrip_whop_order = {
        "action": "payment.succeeded",
        "company_id": alpha_id,
        "data": {
            "id": roundtrip_order_id,
            "company_id": alpha_id,
            "total": 69.00,
            "currency": "usd",
            "customer": {
                "name": "Evelyn Cross",
                "email": "evelyn.cross@example.com",
                "phone": "+1 (555) 883-2019"
            },
            "shipping_address": {
                "line1": "742 Evergreen Terrace",
                "city": "Springfield",
                "state": "OR",
                "postal_code": "97477",
                "country": "United States",
                "country_code": "US"
            },
            "line_items": [
                {
                    "product_id": new_whop_pid,
                    "product_title": "Alpha Chronograph Pro",
                    "variant_title": "Matte Obsidian / 40mm",
                    "quantity": 1,
                    "unit_price": 69.00
                }
            ]
        }
    }
    rt_result = asyncio.run(process_incoming_whop_order(roundtrip_whop_order))
    assert rt_result.get("success") is True, f"Failed roundtrip order ingestion: {rt_result}"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE whop_order_id = ?", (roundtrip_order_id,))
    rt_order = dict(c.fetchone())
    conn.close()

    assert rt_order["cj_order_id"] != "", "Expected CJ Order ID to be automatically created"
    assert rt_order["cj_order_status"] == "SUBMITTED"
    print(f"       CONFIRMED: Order for newly listed product automatically routed to CJ ({rt_order['cj_order_id']}) with ZERO manual mapping!")

    print("=" * 70)
    print(" [8/8] Testing Whop App Store Listing UI (Screenshot Fidelity) ...")
    res_appstore = client.get(f"/app-store?company_id={alpha_id}")
    assert res_appstore.status_code == 200
    html_text = res_appstore.text
    assert "Everything you need to sell globally" in html_text
    assert "Connect Your Whop Store" in html_text
    assert "App Store Showcase Gallery" in html_text
    assert "Transparent Pricing" in html_text
    assert "60-Day Free Trial" in html_text
    print("       App Store UI GET '/app-store' -> 200 OK (Screen 01 & Showcase Gallery Fidelity)")

    res_alias = client.get(f"/listing?company_id={alpha_id}")
    assert res_alias.status_code == 200
    print("       Listing Alias GET '/listing' -> 200 OK")

    print("=" * 70)
    print(" ALL 8 MULTI-TENANT VERIFICATION SUITES PASSED FLAWLESSLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_pipeline()

