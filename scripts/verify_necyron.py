"""Programmatic verification test for Necyron offline site server."""

import sys
import time
import subprocess
import urllib.request
import urllib.parse
import json
from pathlib import Path

TEST_PORT = 8899
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def test_necyron_server():
    print(f"[*] Launching Necyron server on test port {TEST_PORT}...")
    server_process = subprocess.Popen(
        [sys.executable, str(Path(r"c:\Nyxeris\necyron\server.py")), str(TEST_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    time.sleep(2)  # Allow server to bind

    endpoints = [
        ("/", 200, "Home Page"),
        ("/template-kit/home/", 200, "Template Kit Home"),
        ("/template-kit/about-us/", 200, "About Us Page"),
        ("/template-kit/0ur-team/", 200, "Our Team Page"),
        ("/template-kit/services/", 200, "Services Page"),
        ("/template-kit/project/", 200, "Projects Page"),
        ("/template-kit/pricing/", 200, "Pricing Page"),
        ("/template-kit/blog-post/", 200, "Blog Listing Page"),
        ("/template-kit/faq/", 200, "FAQ Page"),
        ("/template-kit/contact-us/", 200, "Contact Page"),
        ("/2026/04/25/advanced-cybersecurity-systems/", 200, "Single Article 1"),
        ("/category/uncategorized/", 200, "Category Page"),
        ("/wp-content/plugins/elementor/assets/css/frontend.min.css", 200, "Elementor CSS"),
        ("/wp-content/plugins/elementor/assets/lib/eicons/fonts/eicons.woff2", 200, "Eicons WOFF2 Font"),
        ("/wp-content/uploads/sites/86/2026/04/Group-3-5-1024x243.png", 200, "Header Logo Image"),
        ("/assets/fonts/google/google_font_1.css", 200, "Offline Google Font CSS"),
        ("/non-existent-page-test", 404, "404 Error Handler"),
    ]

    passed = 0
    failed = 0

    try:
        for path, expected_status, label in endpoints:
            url = f"{BASE_URL}{path}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "NecyronVerifier/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    status = resp.status
                    body = resp.read()
                    if status == expected_status:
                        print(f" [PASS] {label}: {path} -> HTTP {status} (Bytes: {len(body)})")
                        passed += 1
                    else:
                        print(f" [FAIL] {label}: {path} -> Expected {expected_status}, got {status}")
                        failed += 1
            except urllib.error.HTTPError as he:
                if he.code == expected_status:
                    print(f" [PASS] {label}: {path} -> HTTP {he.code} (Expected error status verified)")
                    passed += 1
                else:
                    print(f" [FAIL] {label}: {path} -> Expected {expected_status}, got HTTP {he.code}")
                    failed += 1
            except Exception as e:
                print(f" [ERROR] {label}: {path} -> {e}")
                failed += 1

        # Test POST mock ajax
        try:
            req = urllib.request.Request(
                f"{BASE_URL}/wp-admin/admin-ajax.php",
                data=b"action=test",
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success") is True:
                    print(" [PASS] Mock admin-ajax.php POST -> Handled locally with success response")
                    passed += 1
                else:
                    print(f" [FAIL] Mock admin-ajax.php POST -> Unexpected payload: {data}")
                    failed += 1
        except Exception as e:
            print(f" [ERROR] Mock admin-ajax.php POST -> {e}")
            failed += 1

    finally:
        print("\n[*] Shutting down test server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except Exception:
            server_process.kill()

    print("=" * 60)
    print(f"VERIFICATION SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    test_necyron_server()
