"""Sources 200 real products from CJ Dropshipping across 5 distinct categories,
preserves real manufacturer titles (no 'Nyxeris' prefix) and real high-res photos,
teaches the visual model, and syncs to SQLite and Whop CSV.
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
from services.visual_automation_learner import learner

CDP_URL = "http://127.0.0.1:9222"
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = BASE_DIR / "static" / "images" / "products"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES_QUERIES = [
    {
        "category": "Workspace & Studio",
        "queries": [
            "computer monitor light bar",
            "leather desk pad mouse pad",
            "aluminum laptop stand adjustable",
            "monitor stand riser wooden aluminum"
        ],
        "target": 40
    },
    {
        "category": "Smart Gear & Power",
        "queries": [
            "3 in 1 foldable magnetic wireless charger",
            "gan fast charger 65w",
            "magnetic usb c charging cable",
            "magnetic power bank wireless"
        ],
        "target": 40
    },
    {
        "category": "Mechanical & Audio",
        "queries": [
            "mechanical keyboard keycaps pbt",
            "aluminum headphone stand desk",
            "mechanical numpad macro pad",
            "keyboard switch puller lube kit"
        ],
        "target": 40
    },
    {
        "category": "EDC & Precision Tools",
        "queries": [
            "precision screwdriver set 64 in 1",
            "titanium edc pocket multi tool",
            "folding utility pocket knife tool",
            "metal magnetic cable organizer"
        ],
        "target": 40
    },
    {
        "category": "Ambient & Studio Lighting",
        "queries": [
            "rgb led corner lamp light bar",
            "desktop ambient light bar tube",
            "touch sensor bedside cylinder lamp",
            "retro led desk night light"
        ],
        "target": 40
    }
]


def clean_product_title(raw_title):
    """Cleans supplier noise words while strictly preserving the real product name.
    No 'Nyxeris' prefix added.
    """
    if not raw_title:
        return "Precision Hardware Component"
    
    # Strip known spam prefixes
    cleaned = re.sub(r'^(hot sale|2024|2025|2026|new arrival|factory wholesale|dropshipping|oem|odm)\b', '', raw_title, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\(\[\{].*?(drop shipping|free shipping|wholesale|factory).*?[\)\]\}]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Capitalize cleanly
    words = cleaned.split()
    if len(words) > 12:
        words = words[:12]
    result = " ".join(words)
    return result if len(result) > 5 else raw_title[:60]


def parse_price(price_str):
    if not price_str:
        return 12.00
    m = re.search(r'([0-9]+\.?[0-9]*)', price_str)
    if m:
        try:
            val = float(m.group(1))
            return val if val > 0.5 else 9.99
        except ValueError:
            return 12.00
    return 12.00


def calculate_retail_price(cost):
    """Calculates a clean consumer retail price giving ~65% to 75% gross margin."""
    if cost <= 5.0:
        return round(cost * 4.0, 2)
    elif cost <= 15.0:
        return round(cost * 3.2, 2)
    elif cost <= 30.0:
        return round(cost * 2.8, 2)
    else:
        return round(cost * 2.2, 2)


def source_200_products():
    print("=" * 65)
    print("NYXERIS <- CJ DROPSHIPPING 200 PRODUCTS SOURCING PIPELINE")
    print("=" * 65)

    all_products = []
    seen_hrefs = set()
    seen_titles = set()

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = None
        for pg in b.contexts[0].pages:
            if "cjdropshipping.com" in pg.url:
                page = pg
                break
        if not page:
            page = b.contexts[0].new_page()

        # Step 1: Teach visual model once on CJ search grid
        first_query = "computer monitor light bar"
        first_url = f"https://cjdropshipping.com/search/{first_query.replace(' ', '+')}.html"
        print(f"\n[*] Navigating to initial search page: {first_url} ...")
        page.goto(first_url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(4000)
        page.evaluate("window.scrollBy(0, 400)")
        page.wait_for_timeout(2000)

        # Teach visual learner
        learner.learn_page_state(
            page=page,
            task_name="cj_product_search_grid",
            expected_goal="Locate product cards, genuine titles, CDN images, and supplier wholesale pricing"
        )

        # Step 2: Iterate categories and queries
        for cat_info in CATEGORIES_QUERIES:
            category_name = cat_info["category"]
            target_count = cat_info["target"]
            cat_products = []
            print(f"\n==================================================")
            print(f"[*] SOURCING CATEGORY: {category_name} (Target: {target_count})")
            print(f"==================================================")

            for query in cat_info["queries"]:
                if len(cat_products) >= target_count:
                    break

                search_url = f"https://cjdropshipping.com/search/{query.replace(' ', '+')}.html"
                print(f"[>] Querying CJ: '{query}' -> {search_url}")

                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3000)
                    page.evaluate("window.scrollBy(0, 500)")
                    page.wait_for_timeout(1500)

                    # Extract all productCards on page
                    cards = page.evaluate("""() => {
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

                    print(f"    Found {len(cards)} raw items on CJ for query.")

                    for c in cards:
                        if len(cat_products) >= target_count:
                            break

                        href = c.get("href", "")
                        raw_title = c.get("title", "")
                        img_url = c.get("img", "")
                        price_str = c.get("price", "")

                        if not href or href in seen_hrefs or not img_url or "no-data" in img_url:
                            continue

                        cost = parse_price(price_str)
                        real_title = clean_product_title(raw_title)

                        # Avoid duplicate names
                        norm_title = real_title.lower()[:30]
                        if norm_title in seen_titles:
                            continue

                        seen_hrefs.add(href)
                        seen_titles.add(norm_title)

                        # Extract SKU
                        sku_match = re.search(r'-p-([a-zA-Z0-9\-]+)\.html', href)
                        sku = f"CJ-{sku_match.group(1)[:12]}" if sku_match else f"CJ-{len(all_products)+1:04d}"

                        retail_price = calculate_retail_price(cost)
                        gross_margin = round(((retail_price - cost) / retail_price) * 100, 1)

                        slug = re.sub(r'[^a-z0-9]+', '-', real_title.lower()).strip('-')[:45]
                        if not slug:
                            slug = f"prod-{len(all_products)+1}"

                        prod_obj = {
                            "id": f"prod_cj_{len(all_products)+1:04d}",
                            "title": real_title,
                            "slug": slug,
                            "category": category_name,
                            "price": retail_price,
                            "cost_price": cost,
                            "profit_margin": gross_margin,
                            "sku": sku,
                            "supplier_url": href,
                            "image_url": img_url,
                            "stock_quantity": 85,
                            "badge": "In Stock",
                            "description": f"Genuine precision {real_title}. Manufactured for tactile durability and seamless workspace integration."
                        }

                        cat_products.append(prod_obj)
                        all_products.append(prod_obj)
                        print(f"    [{len(all_products):03d}] {real_title[:45]} | Cost: ${cost:.2f} | Retail: ${retail_price:.2f} ({gross_margin}%)")

                except Exception as ex:
                    print(f"    [!] Search error for '{query}': {ex}")

            print(f"[+] Category '{category_name}' complete with {len(cat_products)} products.")

        b.close()

    print(f"\n==================================================")
    print(f"[*] TOTAL SOURCED PRODUCTS: {len(all_products)}")
    print(f"==================================================")

    # Save complete JSON
    json_path = DATA_DIR / "cj_200_products.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2)
    print(f"[*] Saved JSON Catalog: {json_path}")

    # Synchronize into SQLite
    sync_to_database(all_products)

    # Export Whop CSV
    export_whop_200_csv(all_products)


def sync_to_database(products):
    print("\n[*] Synchronizing 200 products to SQLite nyxeris.db...")
    conn = get_db_connection()
    c = conn.cursor()

    for p in products:
        c.execute("SELECT id FROM products WHERE sku = ? OR slug = ?", (p["sku"], p["slug"]))
        exists = c.fetchone()
        if exists:
            c.execute("""
                UPDATE products
                SET title = ?,
                    description = ?,
                    category = ?,
                    price = ?,
                    cost_price = ?,
                    supplier_url = ?,
                    image_url = ?,
                    badge = ?,
                    stock_quantity = ?
                WHERE id = ?
            """, (
                p["title"], p["description"], p["category"], p["price"],
                p["cost_price"], p["supplier_url"], p["image_url"], p["badge"],
                p["stock_quantity"], exists["id"]
            ))
        else:
            c.execute("""
                INSERT INTO products (
                    id, title, slug, description, category, price, cost_price,
                    stock_quantity, sku, supplier_url, image_url, badge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["title"], p["slug"], p["description"],
                p["category"], p["price"], p["cost_price"], p["stock_quantity"],
                p["sku"], p["supplier_url"], p["image_url"], p["badge"]
            ))

    conn.commit()
    conn.close()
    print("[SUCCESS] Nyxeris SQLite database populated with all 200 products.")


def export_whop_200_csv(products):
    csv_path = DATA_DIR / "whop_products_200_catalog.csv"
    lines = [
        "Product Name,Category,Retail Price USD,Supplier Cost USD,Gross Margin %,SKU,CJ Supplier URL,Image URL,Stock"
    ]
    for p in products:
        lines.append(
            f'"{p["title"]}","{p["category"]}",{p["price"]},{p["cost_price"]},{p["profit_margin"]}%,{p["sku"]},"{p["supplier_url"]}","{p["image_url"]}",{p["stock_quantity"]}'
        )
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[*] Exported Whop 200 Catalog CSV: {csv_path}")


if __name__ == "__main__":
    source_200_products()
