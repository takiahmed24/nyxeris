import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def inspect_pricing_fields():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        whop_page = None
        for pg in b.contexts[0].pages:
            if "whop.com" in pg.url and "products/create" in pg.url:
                whop_page = pg
                break
        
        if not whop_page:
            for pg in b.contexts[0].pages:
                if "whop.com" in pg.url:
                    whop_page = pg
                    break

        if not whop_page:
            print("[!] Whop page not found.")
            return

        print("Testing pricing elements on:", whop_page.url)
        
        print("Total frames on page:", len(whop_page.frames))
        for idx, fr in enumerate(whop_page.frames):
            print(f"  Frame {idx}: name='{fr.name}' url='{fr.url}'")

        name_input = whop_page.locator("input[placeholder='Basic access'], input#product\\.title").first
        if name_input:
            print("[*] Filling Name input with: 'Nyxeris Horizon Pro ScreenBar Light' ...")
            name_input.click()
            name_input.fill("Nyxeris Horizon Pro ScreenBar Light")
            whop_page.wait_for_timeout(1000)

        # Look for Create product button in the left panel
        create_btn = whop_page.locator("button:has-text('Create product')").last
        print(f"Create button enabled: {create_btn.is_enabled()}")
        if create_btn.is_enabled():
            print("[*] Clicking 'Create product' button...")
            create_btn.click()
            whop_page.wait_for_timeout(5000)
            print("New URL after creating product:", whop_page.url)
            whop_page.screenshot(path="data/screenshots/whop_after_create.png")
            print("[*] Saved screenshot to data/screenshots/whop_after_create.png")
        else:
            print("[!] Create button is still disabled.")
            whop_page.screenshot(path="data/screenshots/whop_create_disabled.png")

        b.close()

if __name__ == "__main__":
    inspect_pricing_fields()
