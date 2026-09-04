import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def main():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        page.goto("https://whop.com/dashboard/biz_ea3gy6pg50A7px/products/", wait_until="domcontentloaded", timeout=20000)
        print("Waiting for spinner to disappear...")
        page.wait_for_timeout(6000)
        page.screenshot(path="data/screenshots/whop_products_final_list.png")

        # Extract table rows
        products = page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll('tr, div[class*="table-row"], div[role="row"]'));
            const prods = [];
            for (const r of rows) {
                const link = r.querySelector('a[href*="prod_"]');
                const text = r.innerText.trim().replace(/\\n+/g, ' | ');
                if (link) {
                    prods.push({
                        name: link.innerText.trim(),
                        href: link.href,
                        fullRow: text
                    });
                }
            }
            return prods;
        }""")
        print(f"Products listed on Whop ({len(products)}):")
        import pprint
        pprint.pprint(products)

        page.close()
        b.close()

if __name__ == "__main__":
    main()
