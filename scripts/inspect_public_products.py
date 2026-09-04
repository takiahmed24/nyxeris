import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def main():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        page.goto("https://whop.com/nyxeris/products", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(4000)
        page.screenshot(path="data/screenshots/whop_public_products.png")

        items = page.evaluate("""() => {
            const cards = Array.from(document.querySelectorAll('a[href*="/checkout/"], a[href*="/nyxeris/"]'));
            return cards.map(c => ({
                href: c.href,
                text: c.innerText.trim().replace(/\\n+/g, ' | ')
            }));
        }""")
        print("Items on public products page:")
        import pprint
        pprint.pprint(items)
        page.close()
        b.close()

if __name__ == "__main__":
    main()
