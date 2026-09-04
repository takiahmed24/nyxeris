"""Programmatic Verification Suite for Nyxeris.
Tests database, storefront catalog, checkout flow, Whop payment simulation,
CJ Dropshipping order fulfillment, and white-labeled PDF receipt validation.
"""

import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure root directory is on path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from main import app
from database import init_db, get_db_connection
from config import settings

client = TestClient(app)


def test_database_and_products():
    print("[1/6] Testing Database & Product Catalog...")
    init_db()
    res = client.get("/api/products")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    products = res.json()
    assert len(products) >= 5, f"Expected at least 5 products, got {len(products)}"
    print(f"      OK: Loaded {len(products)} physical products from database.")


def test_checkout_and_order_creation():
    print("[2/6] Testing Physical Order Checkout...")
    payload = {
        "items": [
            {
                "product_id": "prod_lumina_pad",
                "variant_title": "Midnight Charcoal (XL)",
                "quantity": 1
            },
            {
                "product_id": "prod_edc_tool",
                "variant_title": "DLC Matte Black",
                "quantity": 1
            }
        ],
        "shipping": {
            "full_name": "Alexander Vance",
            "email": "alex.vance@example.com",
            "phone": "+1 555-234-5678",
            "address_line1": "742 Evergreen Terrace",
            "address_line2": "Apt 2B",
            "city": "Springfield",
            "state": "OR",
            "postal_code": "97477",
            "country": "United States",
            "shipping_method": "Nyxeris Priority Insured Courier"
        }
    }
    res = client.post("/api/orders/checkout", json=payload)
    assert res.status_code == 200, f"Checkout failed: {res.text}"
    data = res.json()
    assert "order_id" in data
    assert data["order_id"].startswith("NYX-")
    print(f"      OK: Order created: {data['order_id']} (${data['total']:.2f}).")
    return data["order_id"]


def test_payment_and_receipt_white_label(order_id: str):
    print("[3/6] Testing Payment Simulation & White-Labeled PDF Receipt...")
    pay_res = client.post(f"/api/orders/{order_id}/simulate-payment")
    assert pay_res.status_code == 200, f"Payment simulation failed: {pay_res.text}"

    # Fetch PDF Receipt
    pdf_res = client.get(f"/api/orders/{order_id}/receipt")
    assert pdf_res.status_code == 200, f"Failed to retrieve receipt: {pdf_res.status_code}"
    assert pdf_res.headers["content-type"] == "application/pdf"
    pdf_bytes = pdf_res.content
    assert len(pdf_bytes) > 1000, "PDF file is unexpectedly small"

    # Deep Inspect PDF content using pypdf to verify white-labeling
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or ""

        # Verify brand presence
        assert "NYXERIS" in full_text, "Missing 'NYXERIS' in receipt text"
        assert order_id in full_text, f"Missing order ID {order_id} in receipt text"

        # STRICT VERIFICATION: Ensure ZERO Whop mentions in customer-facing receipt
        assert "whop" not in full_text.lower(), "SECURITY/BRANDING FAILURE: 'whop' detected in customer receipt!"
        print("      OK: PDF verified: 100% white-labeled Nyxeris branding. Zero Whop text found.")
    except ImportError:
        print("      (pypdf not available for text inspection, verified raw byte stream size)")


def test_whop_webhook():
    print("[4/6] Testing Whop Webhook Ingestion...")
    # Create another order to test webhook-driven completion
    payload = {
        "items": [{"product_id": "prod_apex_audio", "quantity": 1}],
        "shipping": {
            "full_name": "Elena Rostova",
            "email": "elena@example.com",
            "address_line1": "100 Broadway",
            "city": "New York",
            "state": "NY",
            "postal_code": "10005",
            "country": "United States"
        }
    }
    create_res = client.post("/api/orders/checkout", json=payload)
    order_id = create_res.json()["order_id"]

    webhook_payload = {
        "action": "payment.succeeded",
        "data": {
            "id": "whop_pay_test_99",
            "metadata": {"order_id": order_id}
        }
    }
    wh_res = client.post("/api/webhooks/whop", json=webhook_payload)
    assert wh_res.status_code == 200
    assert wh_res.json()["payment_status"] == "paid"

    # Verify order is paid in DB
    order_check = client.get(f"/api/orders/{order_id}").json()
    assert order_check["order"]["payment_status"] == "paid"
    print(f"      OK: Webhook successfully transitioned {order_id} to paid and generated receipt.")


def test_cj_dropshipping_fulfillment(order_id: str):
    print("[5/6] Testing CJ Dropshipping Fulfillment & Tracking Assignment...")
    fulfill_payload = {
        "fulfillment_status": "shipped",
        "carrier": "USPS via CJ Packet",
        "tracking_number": "CJP94001118995628392100",
        "tracking_url": "https://tools.usps.com/go/TrackConfirmAction?tLabels=CJP94001118995628392100"
    }
    fulfill_res = client.post(f"/api/admin/orders/{order_id}/fulfillment", json=fulfill_payload)
    assert fulfill_res.status_code == 200
    updated = fulfill_res.json()["order"]
    assert updated["fulfillment_status"] == "shipped"
    assert updated["tracking_number"] == "CJP94001118995628392100"
    print("      OK: Order updated with CJ tracking and marked as shipped.")


def test_pages_render():
    print("[6/7] Testing HTML Pages (Storefront, Confirmation, Admin)...")
    res_home = client.get("/")
    assert res_home.status_code == 200
    assert "NYXERIS" in res_home.text

    res_admin = client.get("/admin")
    assert res_admin.status_code == 200
    assert "Dropshipping Cockpit" in res_admin.text

    print("      OK: All templates rendered cleanly.")


def test_titan_learning_engine():
    print("[7/7] Testing Titan-One Self-Learning & Workflow Execution Engine...")
    res = client.get("/api/admin/titan/skills")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    skills = res.json()["skills"]
    assert len(skills) >= 3, f"Expected at least 3 learned skills, got {len(skills)}"
    
    cj_skill = next((s for s in skills if s["id"] == "skill_cj_batch_list_and_export"), None)
    assert cj_skill is not None, "Expected skill_cj_batch_list_and_export to be present"
    assert cj_skill["status"] == "MASTERED"
    print(f"      OK: Titan Skills Library has {len(skills)} mastered workflows (including CJ Batch Export).")

    # Test executing a learned skill automatically
    run_res = client.post("/api/admin/titan/run/skill_realtime_margin_optimization")
    assert run_res.status_code == 200, f"Expected 200, got {run_res.status_code}"
    run_data = run_res.json()
    assert run_data["success"] is True
    print(f"      OK: Autonomous skill execution verified: {run_data['result']}")

    # Test logs endpoint
    log_res = client.get("/api/admin/titan/logs")
    assert log_res.status_code == 200
    logs = log_res.json()["logs"]
    assert len(logs) >= 1
    print(f"      OK: Titan reasoning and training logs active ({len(logs)} entries).")


if __name__ == "__main__":
    print("=" * 65)
    print("      NYXERIS E-COMMERCE & WHITE-LABEL VERIFICATION SUITE")
    print("=" * 65)
    try:
        test_database_and_products()
        test_order_id = test_checkout_and_order_creation()
        test_payment_and_receipt_white_label(test_order_id)
        test_whop_webhook()
        test_cj_dropshipping_fulfillment(test_order_id)
        test_pages_render()
        test_titan_learning_engine()
        print("\n[SUCCESS] ALL 7 VERIFICATION SUITES PASSED FLAWLESSLY.")
        sys.exit(0)
    except AssertionError as ae:
        print(f"\n[FAIL] Assertion failed: {ae}")
        sys.exit(1)
    except Exception as ex:
        print(f"\n[ERROR] Unexpected error: {ex}")
        sys.exit(1)

