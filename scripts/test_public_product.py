import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def test_public_product():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        url = "https://whop.com/nyxeris/products/nyxeris-horizon-pro-screenbar-light/"
        print(f"Testing public Whop product URL: {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3500)
        page.screenshot(path="data/screenshots/whop_public_screenbar.png")
        print("Page Title:", page.title())
        print("Page URL:", page.url)

        # Check buy or join buttons
        btns = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button, a'))
                .map(el => ({tag: el.tagName, text: el.innerText.trim().replace(/\\n/g, ' '), href: el.href || ''}))
                .filter(x => x.text && x.text.length < 50);
        }""")
        print(f"Buttons found ({len(btns)}):")
        for b_item in btns[:15]:
            print(f"  [{b_item['tag']}] '{b_item['text']}' -> {b_item['href']}")

        page.close()
        b.close()

if __name__ == "__main__":
    test_public_product()
