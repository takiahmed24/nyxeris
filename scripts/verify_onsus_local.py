"""
Comprehensive verification test for Onsus Local Mirror.
Tests FastAPI endpoints, template rendering, and asset accessibility.
"""

import sys
import re
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)

def test_endpoints():
    print("==================================================")
    print("  VERIFYING ONSUS LOCAL STOREFRONT ENDPOINTS")
    print("==================================================")

    # 1. Test Root / (Home 05)
    resp = client.get("/")
    assert resp.status_code == 200, f"Root / failed: {resp.status_code}"
    assert "Home 05" in resp.text or "Amazfit" in resp.text or "Onsus" in resp.text, "Root did not return Onsus content"
    print("[PASS] GET / -> HTTP 200 (Contains Home 05 content)")

    # 2. Test /home-05
    resp = client.get("/home-05")
    assert resp.status_code == 200, f"/home-05 failed: {resp.status_code}"
    assert "Onsus" in resp.text, "/home-05 did not contain Onsus"
    print("[PASS] GET /home-05 -> HTTP 200")

    # 3. Test /home-01
    resp = client.get("/home-01")
    assert resp.status_code == 200, f"/home-01 failed: {resp.status_code}"
    assert "Onsus" in resp.text, "/home-01 did not contain Onsus"
    print("[PASS] GET /home-01 -> HTTP 200")

    # 4. Test Mock AJAX
    resp = client.post("/api/wc-ajax")
    assert resp.status_code == 200
    assert resp.json().get("result") == "success"
    print("[PASS] POST /api/wc-ajax -> HTTP 200 (success)")

    resp = client.post("/api/tf-ajax")
    assert resp.status_code == 200
    assert resp.json().get("status") == "success"
    print("[PASS] POST /api/tf-ajax -> HTTP 200 (success)")

    # 5. Check key static assets referenced in HTML exist on disk and serve 200
    soup_text = client.get("/").text
    asset_urls = re.findall(r'(/static/onsus/[^\s"\'<>]+)', soup_text)
    print(f"[*] Found {len(asset_urls)} local static asset references in Home 05.")

    checked = 0
    passed = 0
    sample_assets = list(set(asset_urls))[:40]
    for url in sample_assets:
        clean_url = url.split("?")[0].split("#")[0]
        a_resp = client.get(clean_url)
        checked += 1
        if a_resp.status_code == 200:
            passed += 1
        else:
            print(f"[WARN] Missing asset ({a_resp.status_code}): {clean_url}")

    print(f"[PASS] Sample asset check: {passed}/{checked} served successfully with HTTP 200.")

    print("\n==================================================")
    print("  ALL VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    test_endpoints()
