"""Generates a cinematic video recording of the Nyxeris storefront and interaction flow.
Uses Playwright with headless Chromium to capture a high-frame-rate demonstration video.
"""

import sys
import time
import shutil
import threading
from pathlib import Path
import uvicorn
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from main import app

VIDEOS_DIR = BASE_DIR / "static" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
TARGET_VIDEO = VIDEOS_DIR / "nyxeris_hardware_flow.webm"


def run_video_generation():
    print("[*] Starting temporary web server on port 8002...")
    config = uvicorn.Config(app, host="127.0.0.1", port=8002, log_level="warning")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    time.sleep(1.8)

    print("[*] Launching Playwright browser with 1080p 60fps recording...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir=str(VIDEOS_DIR),
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        print("[*] Navigating to Nyxeris Storefront...")
        page.goto("http://127.0.0.1:8002", timeout=20000)
        page.wait_for_timeout(1500)

        # 1. Cinematic Hero Viewing
        page.wait_for_timeout(1500)

        # 2. Smooth scroll flow down to Bento Grid Innovations
        print("[*] Scrolling to Bento Innovations...")
        for step in range(1, 15):
            page.evaluate(f"window.scrollBy(0, 50);")
            page.wait_for_timeout(60)
        page.wait_for_timeout(1500)

        # 3. Scroll to Interactive Dynamic Modes
        print("[*] Demonstrating Interactive Hardware Actuation Modes...")
        for step in range(1, 15):
            page.evaluate(f"window.scrollBy(0, 60);")
            page.wait_for_timeout(60)
        page.wait_for_timeout(1000)

        # Click Studio Writing Mode
        page.evaluate('NyxerisStore.switchInteractiveMode("studio", document.querySelectorAll(".mode-pill")[1])')
        page.wait_for_timeout(1500)

        # Click Dynamic Multi-Point Actuation Mode
        page.evaluate('NyxerisStore.switchInteractiveMode("hybrid", document.querySelectorAll(".mode-pill")[2])')
        page.wait_for_timeout(1500)

        # Click back to Rapid Trigger
        page.evaluate('NyxerisStore.switchInteractiveMode("rapid", document.querySelectorAll(".mode-pill")[0])')
        page.wait_for_timeout(1200)

        # 4. Scroll to Purchasing Bundles & Catalog
        print("[*] Scrolling to Purchasing Bundles & Catalog...")
        for step in range(1, 22):
            page.evaluate(f"window.scrollBy(0, 70);")
            page.wait_for_timeout(60)
        page.wait_for_timeout(1500)

        # 5. Scroll to In The Box Flat-Lay & Tech Specs
        print("[*] Scrolling to In The Box & Specifications...")
        for step in range(1, 20):
            page.evaluate(f"window.scrollBy(0, 60);")
            page.wait_for_timeout(60)
        page.wait_for_timeout(1500)

        # 6. Smooth scroll back to Hero
        print("[*] Smooth scroll back to top...")
        page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
        page.wait_for_timeout(2000)

        # 7. Add Flagship to Bag -> Drawer flows in
        print("[*] Adding hardware to bag & triggering cart drawer...")
        page.evaluate("NyxerisStore.addToCart('prod_obsidian_board')")
        page.wait_for_timeout(2200)

        # 8. Open Checkout Modal
        print("[*] Transitioning to White-Labeled Physical Checkout...")
        page.evaluate("NyxerisStore.openCheckoutModal()")
        page.wait_for_timeout(2500)

        # Close page and context to finalize video file write
        video_path = page.video.path()
        context.close()
        browser.close()

    server.should_exit = True
    print(f"[*] Raw video saved at: {video_path}")

    # Copy / Rename to definitive name
    if Path(video_path).exists():
        shutil.copy(video_path, TARGET_VIDEO)
        print(f"[SUCCESS] Final video flow generated at: {TARGET_VIDEO} ({TARGET_VIDEO.stat().st_size} bytes)")
    else:
        print("[!] Video file was not found.")


if __name__ == "__main__":
    run_video_generation()
