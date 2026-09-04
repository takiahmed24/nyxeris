"""Syncs live products from CJ Dropshipping into Nyxeris database, JSON catalog,
and Whop product import file.
"""

import sys
import json
import time
import re
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path("C:/Nyxeris")
sys.path.insert(0, str(BASE_DIR))

from database import get_db_connection

CDP_URL = "http://127.0.0.1:9222"
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "static" / "images" / "products"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

TARGET_PRODUCTS = [
    {
        "query": "computer+monitor+hanging+light",
        "category": "Workspace & Studio",
        "custom_title": "Nyxeris Horizon Pro ScreenBar Ambient Light",
        "slug": "nyxeris-horizon-screenbar-light",
        "retail_price": 89.00,
        "badge": "Top Rated",
        "features": [
            "Asymmetrical Optical Design (Zero Screen Glare)",
            "Step-less Rotary Wireless Touch Dial (2700K - 6500K)",
            "Precision Aerospace Aluminum Alloy Housing",
            "Auto-Dimming Ambient Lux Sensor"
        ]
    },
    {
        "query": "3+in+1+foldable+magnetic+wireless+charger",
        "category": "Smart Gear & Power",
        "custom_title": "Nyxeris Matrix 3-in-1 Foldable MagSafe Station",
        "slug": "nyxeris-matrix-magsafe-station",
        "retail_price": 95.00,
        "badge": "Qi2 Fast Wireless",
        "features": [
            "15W Full MagSafe Fast Actuation",
            "Foldable Ultra-Compact Aviation Alloy Hinge",
            "Simultaneous iPhone, Apple Watch & AirPods Qi Induction",
            "Integrated Smart Thermal Dissipation"
        ]
    },
    {
        "query": "dual+sided+leather+desk+pad",
        "category": "Workspace & Studio",
        "custom_title": "Nyxeris Lumina Matte Vegan-Leather Desk Mat",
        "slug": "nyxeris-lumina-desk-mat",
        "retail_price": 49.00,
        "badge": "Waterproof",
        "features": [
            "Dual-Tone Reversible Textured Grain",
            "Hydrophobic & Oleophobic Nano-Coated Surface",
            "900mm x 400mm Extended Workspace Footprint",
            "Precision Laser-Beveled Edge Perimeter"
        ]
    },
    {
        "query": "titanium+edc+pry+bar",
        "category": "Accessories & EDC",
        "custom_title": "Nyxeris Vektor Grade-5 Titanium Pocket Multi-Tool",
        "slug": "nyxeris-vektor-titanium-tool",
        "retail_price": 55.00,
        "badge": "Grade 5 Titanium",
        "features": [
            "CNC Machined Ti-6Al-4V Grade-5 Titanium",
            "Beveled Wedge Pry Edge & Bottle Actuator",
            "Integrated 1/4 inch Hex Bit Driver & Tritium Slot",
            "Deep-Carry Stonewashed Titanium Pocket Clip"
        ]
    }
]


def parse_price(price_str):
    """Extracts the first numeric float from a price string like '$12.50-18.00'."""
    if not price_str:
        return 12.00
    m = re.search(r'([0-9]+\.?[0-9]*)', price_str)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return 12.00
    return 12.00


def download_image(url, local_path):
    """Downloads an image from CJ CDN to local static folder."""
    try:
        if not url:
            return None
        # Ensure url has scheme
        if url.startswith("//"):
            url = "https:" + url
        # Remove resize query if present to get best quality
        clean_url = url.split("?")[0]
        req = urllib.request.Request(
            clean_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp, open(local_path, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"    [!] Failed to download image {url[:40]}...: {e}")
        return False


def run_sync():
    print("=" * 60)
    print("NYXERIS <- CJ DROPSHIPPING LIVE CATALOG SYNC")
    print("=" * 60)

    extracted_products = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"[ERROR] Could not connect to Chrome CDP: {e}")
            return

        # Find CJ tab or use page
        page = None
        for pg in browser.contexts[0].pages:
            if "cjdropshipping.com" in pg.url:
                page = pg
                break
        
        if not page:
            page = browser.contexts[0].new_page()

        for item in TARGET_PRODUCTS:
            query = item["query"]
            search_url = f"https://cjdropshipping.com/search/{query}.html"
            print(f"\n[>] Navigating to CJ search: {search_url} ...")
            
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                # Wait for cards to populate
                page.wait_for_timeout(4000)
                # Scroll down slightly to trigger lazy images
                page.evaluate("window.scrollBy(0, 400)")
                page.wait_for_timeout(2000)

                # Extract product cards
                raw_cards = page.evaluate("""() => {
                    const anchors = Array.from(document.querySelectorAll('a[class*="productCard"]'));
                    return anchors.map(a => {
                        const img = a.querySelector('img');
                        const titleEl = a.querySelector('[class*="name"]');
                        const priceEl = a.querySelector('[class*="price"]');
                        return {
                            href: a.href,
                            title: titleEl ? titleEl.innerText.trim() : a.innerText.trim().slice(0, 100),
                            price: priceEl ? priceEl.innerText.trim() : '',
                            img: img ? (img.src || img.getAttribute('data-src') || '') : ''
                        };
                    });
                }""")

                print(f"    Found {len(raw_cards)} cards on CJ for query.")
                if raw_cards:
                    # Pick the best candidate (first one with price and image)
                    selected_card = None
                    for c in raw_cards:
                        if c["img"] and c["price"]:
                            selected_card = c
                            break
                    if not selected_card:
                        selected_card = raw_cards[0]

                    cost = parse_price(selected_card["price"])
                    # Extract SKU from href: product/{name}-p-{SKU}.html
                    sku_match = re.search(r'-p-([a-zA-Z0-9\-]+)\.html', selected_card["href"])
                    cj_sku = f"CJ-{sku_match.group(1)[:12]}" if sku_match else f"CJ-{item['slug'][:8].upper()}"

                    # Download local image
                    img_filename = f"{item['slug']}.jpg"
                    local_img_path = IMAGES_DIR / img_filename
                    download_success = download_image(selected_card["img"], local_img_path)
                    
                    local_img_url = f"/static/images/products/{img_filename}" if download_success else selected_card["img"]

                    prod_data = {
                        "id": f"prod_{item['slug'].replace('-', '_')}",
                        "title": item["custom_title"],
                        "slug": item["slug"],
                        "category": item["category"],
                        "cj_original_title": selected_card["title"],
                        "retail_price": item["retail_price"],
                        "cost_price": cost,
                        "profit_margin": round(((item["retail_price"] - cost) / item["retail_price"]) * 100, 1),
                        "sku": cj_sku,
                        "supplier_url": selected_card["href"],
                        "image_url": local_img_url,
                        "remote_image_url": selected_card["img"],
                        "badge": item["badge"],
                        "features": item["features"]
                    }

                    print(f"    [+] Selected: {prod_data['title']}")
                    print(f"        Supplier Price: ${cost:.2f} | Retail: ${prod_data['retail_price']:.2f} | Margin: {prod_data['profit_margin']}%")
                    print(f"        SKU: {cj_sku}")
                    print(f"        Supplier Link: {selected_card['href']}")
                    print(f"        Image: {local_img_url}")
                    extracted_products.append(prod_data)
                else:
                    print(f"    [!] No cards found for query '{query}'.")

            except Exception as ex:
                print(f"    [!] Error during search for '{query}': {ex}")

        browser.close()

    if not extracted_products:
        print("[!] No products extracted.")
        return

    # Save to JSON
    json_path = DATA_DIR / "cj_live_products.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(extracted_products, f, indent=2)
    print(f"\n[*] Saved catalog JSON: {json_path}")

    # Save to SQLite
    update_database(extracted_products)

    # Export Whop CSV
    export_whop_csv(extracted_products)


def update_database(products):
    conn = get_db_connection()
    cursor = conn.cursor()

    for p in products:
        cursor.execute("SELECT id FROM products WHERE slug = ?", (p["slug"],))
        exists = cursor.fetchone()
        if exists:
            cursor.execute("""
                UPDATE products
                SET title = ?,
                    cost_price = ?,
                    supplier_url = ?,
                    sku = ?,
                    image_url = ?,
                    badge = ?
                WHERE slug = ?
            """, (p["title"], p["cost_price"], p["supplier_url"], p["sku"], p["image_url"], p["badge"], p["slug"]))
        else:
            cursor.execute("""
                INSERT INTO products (
                    id, title, slug, description, category, price, cost_price,
                    stock_quantity, sku, supplier_url, image_url, badge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 50, ?, ?, ?, ?)
            """, (
                p["id"], p["title"], p["slug"],
                f"Precision {p['title']} engineered for daily durability and tactile focus.",
                p["category"], p["retail_price"], p["cost_price"],
                p["sku"], p["supplier_url"], p["image_url"], p["badge"]
            ))

    conn.commit()
    conn.close()
    print("[SUCCESS] Nyxeris SQLite database updated with live supplier links and costs.")


def export_whop_csv(products):
    """Exports CSV formatted for Whop product listing & pricing setup."""
    csv_path = DATA_DIR / "whop_products_catalog.csv"
    lines = [
        "Product Name,Category,Price USD,Cost USD,Gross Margin %,SKU,CJ Supplier URL,Image URL,Key Features"
    ]
    for p in products:
        features_str = " | ".join(p["features"]).replace('"', '""')
        lines.append(
            f'"{p["title"]}","{p["category"]}",{p["retail_price"]},{p["cost_price"]},{p["profit_margin"]}%,{p["sku"]},"{p["supplier_url"]}","{p["image_url"]}","{features_str}"'
        )
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[*] Exported Whop Product CSV: {csv_path}")


if __name__ == "__main__":
    run_sync()
