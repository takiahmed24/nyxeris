"""Programmatic verification test for Next EUV local server."""

import sys
import os
import time
import json
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

TEST_PORT = 8877
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def test_server():
    print(f"[*] Starting Next EUV server on test port {TEST_PORT}...")
    server_process = subprocess.Popen(
        [sys.executable, str(Path(r"c:\Nyxeris\serve_nexteuv.py")), str(TEST_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    time.sleep(2)  # Wait for server to bind

    endpoints = [
        ("/", 200, "Home Root Page"),
        ("/home-1/", 200, "Home 1 (Cars)"),
        ("/home-2/", 200, "Home 2 (Drones)"),
        ("/home-3/", 200, "Home 3 (E-Scooters)"),
        ("/about/", 200, "About Page"),
        ("/service/", 200, "Services Page"),
        ("/pricing-plans/", 200, "Pricing Plans"),
        ("/gallery/", 200, "Gallery Page"),
        ("/faq/", 200, "FAQ Page"),
        ("/contact/", 200, "Contact Page"),
        ("/cart/", 200, "Cart Page"),
        ("/shop-cars/", 200, "Shop Cars"),
        ("/shop-drones/", 200, "Shop Drones"),
        ("/shop-e-scooter/", 200, "Shop E-Scooter"),
        ("/product/smarto-suv/", 200, "Product: Smarto SUV"),
        ("/product/electro-star/", 200, "Product: Electro Star"),
        ("/assets/fonts/google/google_font_1.css", 200, "Offline Google Font Stylesheet"),
        ("/404", 404, "404 Error Page"),
        ("/non-existent-sample-page", 404, "Unknown URL Fallback"),
    ]

    passed = 0
    failed = 0

    try:
        for path, expected_code, label in endpoints:
            url = f"{BASE_URL}{path}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "NextEUVVerifier/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    code = resp.status
                    body = resp.read()
                    ct = resp.headers.get("Content-Type", "")
                    if code == expected_code:
                        print(f" [PASS] {label} ({path}) -> HTTP {code} ({len(body)} bytes, {ct.split(';')[0]})")
                        passed += 1
                    else:
                        print(f" [FAIL] {label} ({path}) -> Expected {expected_code}, got {code}")
                        failed += 1
            except urllib.error.HTTPError as he:
                if he.code == expected_code:
                    print(f" [PASS] {label} ({path}) -> Expected HTTP {he.code} verified")
                    passed += 1
                else:
                    print(f" [FAIL] {label} ({path}) -> Expected {expected_code}, got {he.code}")
                    failed += 1
            except Exception as e:
                print(f" [ERROR] {label} ({path}) -> {e}")
                failed += 1

        # Test POST mock admin-ajax.php
        try:
            req = urllib.request.Request(
                f"{BASE_URL}/wp-admin/admin-ajax.php",
                data=b"action=woocommerce_get_refreshed_fragments",
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success") is True or "fragments" in data:
                    print(" [PASS] Mock admin-ajax.php POST -> Handled locally with success response")
                    passed += 1
                else:
                    print(f" [FAIL] Mock admin-ajax.php POST -> Unexpected payload: {data}")
                    failed += 1
        except Exception as e:
            print(f" [ERROR] Mock admin-ajax.php POST -> {e}")
            failed += 1

    finally:
        print("\n[*] Stopping test server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except Exception:
            server_process.kill()

    print("=" * 65)
    print(f"NEXT EUV VERIFICATION SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 65)
    return failed == 0

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)
