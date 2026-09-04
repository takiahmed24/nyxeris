"""Whop Manager for Nyxeris.
Uses CDP on port 9222 to interact with Whop dashboard,
delegates visual checks to local qwen2.5vl:3b,
and extracts real Whop Product IDs for our storefront.
"""

import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path("C:/Nyxeris")
sys.path.insert(0, str(BASE_DIR))

from services.local_vision import analyze_image_locally
from database import get_db_connection

CDP_URL = "http://127.0.0.1:9222"
SCREENSHOTS_DIR = BASE_DIR / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

REMAINING_PRODUCTS = [
    {
        "slug": "nyxeris-matrix-magsafe-station",
        "title": "Nyxeris Matrix 3-in-1 Foldable MagSafe Station",
        "price": 49.99
    },
    {
        "slug": "nyxeris-lumina-desk-mat",
        "title": "Nyxeris Lumina Matte Vegan-Leather Desk Mat",
        "price": 14.99
    },
    {
        "slug": "nyxeris-vektor-titanium-tool",
        "title": "Nyxeris Vektor Grade-5 Titanium Pocket Multi-Tool",
        "price": 29.99
    }
]


def list_existing_whop_products(page):
    """Scrapes all product rows and links from Whop products page."""
    page.goto("https://whop.com/dashboard/biz_ea3gy6pg50A7px/products/", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(3500)
    
    # Visual check with local vision model
    screenshot_path = SCREENSHOTS_DIR / "whop_products_catalog_list.png"
    page.screenshot(path=str(screenshot_path))
    print(f"[*] Screenshot saved: {screenshot_path}")
    
    print("[*] Running local visual analysis via qwen2.5vl:3b...")
    vision_res = analyze_image_locally(screenshot_path, "List the names of all products visible in this table or page.")
    if vision_res.get("success"):
        print(f"    Local Vision: {vision_res.get('analysis')}")

    # Extract DOM links
    products = page.evaluate("""() => {
        const links = Array.from(document.querySelectorAll('a[href*="/products/prod_"]'));
        const seen = new Map();
        for (const a of links) {
            const href = a.href;
            const text = a.innerText.trim();
            const idMatch = href.match(/prod_[a-zA-Z0-9]+/);
            const prodId = idMatch ? idMatch[0] : null;
            if (prodId && !seen.has(prodId)) {
                seen.set(prodId, {
                    id: prodId,
                    href: href,
                    name: text
                });
            }
        }
        return Array.from(seen.values());
    }""")
    return products


def create_product_on_whop(page, title):
    """Navigates to Whop product creation, fills title, and clicks create."""
    print(f"\n[+] Creating product on Whop: '{title}' ...")
    create_url = "https://whop.com/dashboard/biz_ea3gy6pg50A7px/products/create"
    page.goto(create_url, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(3000)

    name_input = page.locator("input[placeholder='Basic access'], input#product\\.title").first
    if not name_input.is_visible():
        print("    [!] Name input not found!")
        return None

    name_input.click()
    name_input.fill(title)
    page.wait_for_timeout(1000)

    create_btn = page.locator("button:has-text('Create product')").last
    if not create_btn.is_enabled():
        print("    [!] Create button not enabled!")
        return None

    create_btn.click()
    page.wait_for_timeout(4000)

    # Check resulting URL for createdProductId
    curr_url = page.url
    print(f"    Result URL: {curr_url}")
    import re
    m = re.search(r'prod_[a-zA-Z0-9]+', curr_url)
    prod_id = m.group(0) if m else None

    # Screenshot and local vision check
    snap_path = SCREENSHOTS_DIR / f"whop_created_{title[:12].replace(' ', '_')}.png"
    page.screenshot(path=str(snap_path))
    
    return prod_id


def run_full_whop_sync():
    print("=" * 60)
    print("NYXERIS <- WHOP AUTOMATION & LOCAL VISION PIPELINE")
    print("=" * 60)

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        whop_page = None
        for pg in b.contexts[0].pages:
            if "whop.com" in pg.url:
                whop_page = pg
                break
        
        if not whop_page:
            whop_page = b.contexts[0].new_page()

        # Step 1: Check existing products
        existing = list_existing_whop_products(whop_page)
        print(f"\n[*] Found {len(existing)} existing products on Whop:")
        for ep in existing:
            print(f"    ID: {ep['id']} | Name: {ep['name']} | URL: {ep['href']}")

        # Map for storing slug -> whop_id
        whop_id_map = {
            "nyxeris-horizon-screenbar-light": "prod_AvrTlUnUF27GJ"
        }

        # Step 2: Create remaining products
        for prod in REMAINING_PRODUCTS:
            title = prod["title"]
            slug = prod["slug"]
            
            # Check if already exists in existing
            found_id = None
            for ep in existing:
                if slug in ep["name"].lower() or title.lower() in ep["name"].lower():
                    found_id = ep["id"]
                    break
            
            if not found_id:
                found_id = create_product_on_whop(whop_page, title)
            
            if found_id:
                print(f"    [SUCCESS] Assigned Whop ID: {found_id} to '{title}'")
                whop_id_map[slug] = found_id
            else:
                print(f"    [!] Could not get Whop ID for '{title}'")

        # Step 3: Update local database with real Whop IDs
        print("\n[*] Updating Nyxeris SQLite database with real Whop Product IDs...")
        conn = get_db_connection()
        c = conn.cursor()
        for slug, w_id in whop_id_map.items():
            c.execute("UPDATE products SET whop_product_id = ? WHERE slug = ?", (w_id, slug))
            print(f"    Updated {slug} -> whop_product_id = {w_id}")
        conn.commit()
        conn.close()

        # Save mapping to JSON
        map_path = BASE_DIR / "data" / "whop_product_ids.json"
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(whop_id_map, f, indent=2)
        print(f"\n[SUCCESS] Whop Product IDs saved to: {map_path}")

        b.close()


if __name__ == "__main__":
    run_full_whop_sync()
