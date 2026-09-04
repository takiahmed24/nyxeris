import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def test_direct_checkout():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        url = "https://whop.com/checkout/prod_AvrTlUnUF27GJ"
        print(f"Testing direct Whop checkout URL: {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3500)
        page.screenshot(path="data/screenshots/whop_direct_checkout.png")
        print("Page Title:", page.title())
        print("Page URL:", page.url)
        page.close()
        b.close()

if __name__ == "__main__":
    test_direct_checkout()
