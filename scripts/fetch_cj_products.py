"""Scrapes winning products directly from the user's authenticated CJ Dropshipping browser session
and saves them into Nyxeris database.
"""

import sys
import json
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database import get_db_connection

CDP_URL = "http://127.0.0.1:9222"
DATA_FILE = BASE_DIR / "data" / "cj_scraped_products.json"

SEARCH_QUERIES = [
    {
        "category": "Workspace & Studio",
        "query": "Screenbar monitor light",
        "custom_title": "Nyxeris Horizon Pro ScreenBar Ambient Light",
        "slug": "nyxeris-horizon-screenbar-light",
        "retail_price": 89.00,
        "badge": "Top Rated"
    },
    {
        "category": "Smart Gear & Power",
        "query": "3 in 1 foldable magnetic wireless charger aluminum",
        "custom_title": "Nyxeris Matrix 3-in-1 Foldable MagSafe Station",
        "slug": "nyxeris-matrix-magsafe-station",
        "retail_price": 95.00,
        "badge": "Qi2 Fast Wireless"
    },
    {
        "category": "Workspace & Studio",
        "query": "dual sided leather desk pad",
        "custom_title": "Nyxeris Lumina Matte Vegan-Leather Desk Mat",
        "slug": "nyxeris-lumina-desk-mat",
        "retail_price": 49.00,
        "badge": "Waterproof"
    },
    {
        "category": "Accessories & EDC",
        "query": "titanium EDC pry bar multi tool",
        "custom_title": "Nyxeris Vektor Grade-5 Titanium Pocket Multi-Tool",
        "slug": "nyxeris-vektor-titanium-tool",
        "retail_price": 55.00,
        "badge": "Grade 5 Titanium"
    }
]


def extract_products_from_cj():
    print("[*] Connecting to real Chrome browser session over CDP...")
    scraped_data = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            print(f"[ERROR] Could not connect to Chrome: {e}")
            return []

        context = browser.contexts[0]
        tab = None
        for pg in context.pages:
            if "cjdropshipping.com" in pg.url:
                tab = pg
                break

        if not tab:
            print("[*] No active CJ Dropshipping tab found, creating a new tab in your browser...")
            tab = context.new_page()

        for item in SEARCH_QUERIES:
            query = item["query"]
            print(f"\n[>] Searching CJ Dropshipping for: '{query}' ...")
            encoded_query = query.replace(" ", "%20")
            search_url = f"https://cjdropshipping.com/list/wholesale-products-list.html?key={encoded_query}"
            
            try:
                tab.goto(search_url, timeout=25000)
                tab.wait_for_timeout(4000)

                # Scroll down slightly to trigger lazy image loads
                tab.evaluate("window.scrollBy(0, 500)")
                tab.wait_for_timeout(1500)

                # Extract product cards
                products_js = """
                () => {
                    const cards = document.querySelectorAll('.product-item, .item-box, .goods-box, a[href*="product-detail"]');
                    const results = [];
                    const seenHrefs = new Set();

                    for (const el of cards) {
                        let linkEl = el.tagName === 'A' ? el : el.querySelector('a[href*="product-detail"]');
                        if (!linkEl) continue;
                        const href = linkEl.href;
                        if (seenHrefs.has(href)) continue;
                        seenHrefs.add(href);

                        let imgEl = el.querySelector('img');
                        let imgSrc = imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '';
                        let title = linkEl.getAttribute('title') || linkEl.innerText || el.innerText || '';
                        
                        // Extract price text
                        let priceText = '';
                        let priceEl = el.querySelector('.price, .item-price, [class*="price"]');
                        if (priceEl) priceText = priceEl.innerText;

                        if (title.length > 5) {
                            results.push({
                                title: title.replace(/\\n/g, ' ').trim().slice(0, 100),
                                href: href,
                                img: imgSrc,
                                price_raw: priceText
                            });
                        }
                        if (results.length >= 3) break;
                    }
                    return results;
                }
                """
                found = tab.evaluate(products_js)
                print(f"    Found {len(found)} candidate products on CJ.")

                if found:
                    top_prod = found[0]
                    # Parse numeric price
                    price_match = re.search(r'[\$]?([0-9]+\.?[0-9]*)', top_prod.get("price_raw", ""))
                    cost_price = float(price_match.group(1)) if price_match else 15.00

                    img_url = top_prod.get("img") or ""
                    if not img_url.startswith("http"):
                        img_url = "https:" + img_url if img_url.startswith("//") else img_url

                    sku_match = re.search(r'product-detail/([a-zA-Z0-9\-]+)', top_prod.get("href", ""))
                    cj_sku = f"CJ-{sku_match.group(1)[:12]}" if sku_match else f"CJ-{query[:4].upper()}-01"

                    record = {
                        "id": f"prod_cj_{item['slug'].replace('-', '_')[:16]}",
                        "title": item["custom_title"],
                        "slug": item["slug"],
                        "category": item["category"],
                        "cj_title": top_prod["title"],
                        "price": item["retail_price"],
                        "cost_price": cost_price,
                        "sku": cj_sku,
                        "supplier_url": top_prod["href"],
                        "image_url": img_url,
                        "badge": item["badge"]
                    }
                    print(f"    Selected: {record['title']} | Supplier Cost: ${cost_price:.2f} | Retail: ${record['price']:.2f}")
                    print(f"    Supplier Link: {record['supplier_url']}")
                    scraped_data.append(record)
                else:
                    print(f"    [!] No cards matched for {query}, keeping existing catalog.")

            except Exception as e:
                print(f"    [!] Error searching for '{query}': {e}")

        browser.close()

    return scraped_data


def save_to_database(products):
    if not products:
        print("[!] No new products to save.")
        return

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2)
    print(f"\n[*] Saved {len(products)} products to {DATA_FILE}")

    conn = get_db_connection()
    cursor = conn.cursor()

    for p in products:
        # Check if exists
        cursor.execute("SELECT id FROM products WHERE slug = ?", (p["slug"],))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE products 
                SET cost_price = ?,
                    supplier_url = ?,
                    sku = COALESCE(?, sku)
                WHERE slug = ?
            """, (p["cost_price"], p["supplier_url"], p["sku"], p["slug"]))
            if p.get("image_url") and p["image_url"].startswith("http"):
                cursor.execute("UPDATE products SET image_url = ? WHERE slug = ?", (p["image_url"], p["slug"]))
        else:
            cursor.execute("""
                INSERT INTO products (
                    id, title, slug, description, category, price, cost_price,
                    stock_quantity, sku, supplier_url, image_url, badge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 50, ?, ?, ?, ?)
            """, (
                p["id"], p["title"], p["slug"],
                f"Precision {p['title']} engineered for daily durability and tactile focus.",
                p["category"], p["price"], p["cost_price"],
                p["sku"], p["supplier_url"], p["image_url"], p["badge"]
            ))

    conn.commit()
    conn.close()
    print("[SUCCESS] Nyxeris database updated with live CJ Dropshipping supplier links & costs.")


if __name__ == "__main__":
    items = extract_products_from_cj()
    save_to_database(items)
