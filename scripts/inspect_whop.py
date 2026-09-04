import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def main():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        whop_page = None
        for pg in b.contexts[0].pages:
            if "whop.com" in pg.url:
                whop_page = pg
                break
        
        if not whop_page:
            print("[!] Whop page not found.")
            return

        print("Found Whop Tab:")
        print("  Title:", whop_page.title())
        print("  URL:", whop_page.url)

        prod_url = "https://whop.com/dashboard/biz_ea3gy6pg50A7px/products/"
        print(f"Navigating to Whop Products: {prod_url} ...")
        whop_page.goto(prod_url, wait_until="domcontentloaded", timeout=20000)
        whop_page.wait_for_timeout(4000)
        
        whop_page.screenshot(path="data/screenshots/whop_products_page.png")
        print("[*] Saved screenshot to data/screenshots/whop_products_page.png")

        prod_btn = whop_page.locator("button:has-text('Create product'), a:has-text('Create product')").first
        if prod_btn:
            print("[*] Clicking 'Create product' ...")
            prod_btn.click()
            whop_page.wait_for_timeout(3000)
            whop_page.screenshot(path="data/screenshots/whop_create_product_modal.png")
            print("[*] Saved screenshot to data/screenshots/whop_create_product_modal.png")
            print("Current URL:", whop_page.url)

            # Inspect inputs in the modal/form
            form_inputs = whop_page.evaluate("""() => {
                const inputs = Array.from(document.querySelectorAll('input, textarea, select, [contenteditable="true"]'));
                const buttons = Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim()).filter(Boolean);
                return {
                    inputs: inputs.map(i => ({
                        tag: i.tagName,
                        type: i.type,
                        name: i.name,
                        placeholder: i.placeholder,
                        id: i.id,
                        ariaLabel: i.getAttribute('aria-label') || ''
                    })),
                    buttons: buttons.slice(0, 15)
                };
            }""")
            print("Form inputs and buttons:")
            import pprint
            pprint.pprint(form_inputs)
        b.close()

if __name__ == "__main__":
    main()
