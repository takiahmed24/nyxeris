"""
Live TCP test to verify uvicorn serves Onsus Home 05 on http://127.0.0.1:8000
and cleans up afterwards.
"""

import subprocess
import time
import urllib.request
import sys

print("[*] Starting uvicorn on port 8000...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

try:
    # Wait for server to boot
    time.sleep(2.5)
    
    # Test Home 05 (Root)
    print("[*] Testing HTTP GET http://127.0.0.1:8000/ ...")
    req = urllib.request.Request("http://127.0.0.1:8000/")
    with urllib.request.urlopen(req, timeout=5) as resp:
        content = resp.read().decode("utf-8", errors="ignore")
        assert resp.status == 200
        assert "Home 05" in content or "Onsus" in content
        print(f"[PASS] HTTP 200 OK, Received {len(content)} bytes for Home 05 storefront!")

    # Test Home 01
    print("[*] Testing HTTP GET http://127.0.0.1:8000/home-01 ...")
    req = urllib.request.Request("http://127.0.0.1:8000/home-01")
    with urllib.request.urlopen(req, timeout=5) as resp:
        content = resp.read().decode("utf-8", errors="ignore")
        assert resp.status == 200
        print(f"[PASS] HTTP 200 OK, Received {len(content)} bytes for Home 01 storefront!")

    # Test a static CSS asset
    print("[*] Testing HTTP GET http://127.0.0.1:8000/static/onsus/wp-content/themes/onsus/css/bootstrap.css ...")
    req = urllib.request.Request("http://127.0.0.1:8000/static/onsus/wp-content/themes/onsus/css/bootstrap.css")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        print(f"[PASS] Static asset served with HTTP 200 OK!")

finally:
    print("[*] Shutting down uvicorn test process...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    print("[OK] Test completed and process cleanly shut down.")
