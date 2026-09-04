"""Browser Controller for Nyxeris.
Connects directly to the user's running real Chrome instance over Chrome DevTools Protocol (CDP)
at port 9222, reusing all real human sessions, logins, cookies, and bypassing anti-bot shields.
"""

import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"
SCREENSHOTS_DIR = Path("C:/Nyxeris/data/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def check_status():
    """Checks if the user's browser is active and lists open tabs."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0]
            pages = context.pages
            print(f"[SUCCESS] Connected to real Chrome! Active tabs: {len(pages)}")
            for idx, pg in enumerate(pages):
                print(f"  Tab {idx + 1}: [{pg.title()}] -> {pg.url}")
            browser.close()
            return True
    except Exception as e:
        print(f"[ERROR] Could not connect to real Chrome on {CDP_URL}.")
        print("Make sure you started the browser by double-clicking 'launch_browser.bat'.")
        print(f"Details: {e}")
        return False


def take_screenshot(name="active_tab"):
    """Takes a screenshot of the currently active tab."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            page = browser.contexts[0].pages[0]
            file_path = SCREENSHOTS_DIR / f"{name}.png"
            page.screenshot(path=str(file_path), full_page=False)
            print(f"[SCREENSHOT] Captured: {file_path}")
            browser.close()
            return str(file_path)
    except Exception as e:
        print(f"[ERROR] Screenshot failed: {e}")
        return None


def navigate_to(url):
    """Navigates the primary tab to a given URL."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            page = browser.contexts[0].pages[0]
            print(f"Navigating tab to: {url} ...")
            page.goto(url, timeout=30000)
            print(f"Loaded: [{page.title()}] -> {page.url}")
            browser.close()
    except Exception as e:
        print(f"[ERROR] Navigation failed: {e}")


def get_page_content():
    """Returns the title and text of the primary tab."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            page = browser.contexts[0].pages[0]
            title = page.title()
            url = page.url
            text_snippet = page.inner_text("body")[:1000]
            print(f"Title: {title}")
            print(f"URL: {url}")
            print(f"Text Snippet:\n{text_snippet}...")
            browser.close()
    except Exception as e:
        print(f"[ERROR] Failed to get page content: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        check_status()
    else:
        cmd = sys.argv[1].lower()
        if cmd == "status":
            check_status()
        elif cmd == "screenshot":
            name = sys.argv[2] if len(sys.argv) > 2 else "tab_capture"
            take_screenshot(name)
        elif cmd == "goto" and len(sys.argv) > 2:
            navigate_to(sys.argv[2])
        elif cmd == "content":
            get_page_content()
        else:
            print(f"Unknown command: {cmd}")
