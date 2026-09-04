import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def check_product_details():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        
        url = "https://whop.com/dashboard/biz_ea3gy6pg50A7px/products/prod_AvrTlUnUF27GJ/"
        print(f"Opening product details: {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3500)
        page.screenshot(path="data/screenshots/whop_prod_detail.png")
        print("Page Title:", page.title())
        print("Page URL:", page.url)

        # Check links, tabs, and buttons
        elements = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a, button')).map(el => ({
                tag: el.tagName,
                text: el.innerText.trim().replace(/\\n/g, ' '),
                href: el.href || ''
            })).filter(x => x.text && x.text.length < 50);
            return links;
        }""")
        print(f"Found {len(elements)} elements on product detail:")
        for el in elements[:20]:
            print(f"  [{el['tag']}] {el['text']} -> {el['href']}")

        page.close()
        b.close()

if __name__ == "__main__":
    check_product_details()
