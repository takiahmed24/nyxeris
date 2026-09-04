import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def test_paid_access():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        url = "https://whop.com/dashboard/biz_ea3gy6pg50A7px/products/prod_AvrTlUnUF27GJ/"
        print(f"Navigating to: {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)

        # Click Paid access button
        paid_btn = page.locator("button:has-text('Paid access'), div:has-text('Paid access')").last
        print("[*] Clicking 'Paid access'...")
        paid_btn.click()
        page.wait_for_timeout(1500)

        # Toggle 'Collect shipping address'
        shipping_toggle = page.locator("text='Collect shipping address'").locator("xpath=..").locator("input[type='checkbox'], button[role='switch']").first
        if shipping_toggle.is_visible():
            print("[*] Toggling 'Collect shipping address'...")
            shipping_toggle.click()
            page.wait_for_timeout(1000)

        page.screenshot(path="data/screenshots/whop_paid_access_opened.png")
        print("[*] Saved screenshot to data/screenshots/whop_paid_access_opened.png")

        # Check what inputs are visible now
        inputs = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input, select, textarea')).map(i => ({
                tag: i.tagName,
                type: i.type,
                placeholder: i.placeholder,
                value: i.value,
                id: i.id,
                name: i.name
            }));
        }""")
        print("Visible inputs after selecting Paid access:")
        import pprint
        pprint.pprint(inputs)

        page.close()
        b.close()

if __name__ == "__main__":
    test_paid_access()
