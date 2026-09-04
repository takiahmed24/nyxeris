import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        page = None
        for pg in browser.contexts[0].pages:
            if "cjdropshipping.com" in pg.url:
                page = pg
                break
        
        if not page:
            print("No CJ tab found.")
            return

        print(f"Current CJ URL: {page.url}")
        print(f"Current CJ Title: {page.title()}")

        print(f"Opening My CJ dashboard in a secondary page...")
        my_page = browser.contexts[0].new_page()
        my_page.goto("https://cjdropshipping.com/my.html#/dashboard", timeout=25000)
        my_page.wait_for_timeout(4000)
        print(f"My CJ Page Title: {my_page.title()}")
        print(f"My CJ Page URL: {my_page.url}")

        dashboard_text = my_page.inner_text("body")[:1000]
        print("Dashboard Snippet:\n", dashboard_text)
        my_page.screenshot(path="data/screenshots/my_cj_dashboard.png")
        my_page.close()
        browser.close()

if __name__ == "__main__":
    main()
