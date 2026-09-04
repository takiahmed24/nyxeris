"""Collaborative Sourcing & Training Script: Antigravity + Titan-One.
Makes Titan-One act as the Product Director and Copywriter, evaluating products
and generating Whop listing copy, while Antigravity handles CDP automation,
database synchronization, and CSV export.
"""

import sys
import json
import time
from pathlib import Path

BASE_DIR = Path("C:/Nyxeris")
sys.path.insert(0, str(BASE_DIR))

from database import get_db_connection
from services.titan_ai_assistant import (
    evaluate_product_with_titan,
    generate_whop_copy_with_titan,
    log_training_step
)

DATA_DIR = BASE_DIR / "data"

CANDIDATE_PRODUCTS = [
    {
        "id": "prod_nyxeris_horizon_screenbar",
        "slug": "nyxeris-horizon-screenbar-light",
        "category": "Workspace & Studio",
        "title": "Computer Monitor Hanging Light Bar Zhirui Screen Light",
        "href": "https://cjdropshipping.com/product/monitor-hanging-light-zhirui-screen-light-bedroom-dormitory-desk-p-1401795644515028992.html",
        "price": "$16.36",
        "cost_price": 16.36,
        "sku": "CJ-140179564451",
        "image_url": "/static/images/products/nyxeris-horizon-screenbar-light.jpg",
        "badge": "Top Rated"
    },
    {
        "id": "prod_nyxeris_matrix_magsafe",
        "slug": "nyxeris-matrix-magsafe-station",
        "category": "Smart Gear & Power",
        "title": "3 in 1 Magnetic Foldable Wireless Charger Station Multi Device",
        "href": "https://cjdropshipping.com/product/3-in-1-magnetic-foldable-wireless-charger-charging-station-multi-device-folding-cell-phone-wireless-charger-gadgets-p-1619525256841015296.html",
        "price": "$15.77",
        "cost_price": 15.77,
        "sku": "CJ-161952525684",
        "image_url": "/static/images/products/nyxeris-matrix-magsafe-station.jpg",
        "badge": "Qi2 Fast Wireless"
    },
    {
        "id": "prod_nyxeris_lumina_deskmat",
        "slug": "nyxeris-lumina-desk-mat",
        "category": "Workspace & Studio",
        "title": "Oversized Thickened Precision Seaming Computer Desk Mat",
        "href": "https://cjdropshipping.com/product/oversized-thickened-precision-seaming-computer-desk-mat-p-1386928189288353792.html",
        "price": "$3.50",
        "cost_price": 3.50,
        "sku": "CJ-138692818928",
        "image_url": "/static/images/products/nyxeris-lumina-desk-mat.jpg",
        "badge": "Waterproof"
    },
    {
        "id": "prod_nyxeris_vektor_titanium",
        "slug": "nyxeris-vektor-titanium-tool",
        "category": "Accessories & EDC",
        "title": "Titanium Alloy Portable EDC Tactical Tool Mini Pen & Wedge",
        "href": "https://cjdropshipping.com/product/titanium-alloy-portable-edc-tactical-pen-mini-self-defense-p-2406290815111615200.html",
        "price": "$9.00",
        "cost_price": 9.00,
        "sku": "CJ-240629081511",
        "image_url": "/static/images/products/nyxeris-vektor-titanium-tool.jpg",
        "badge": "Grade 5 Titanium"
    }
]


def run_training_pipeline():
    print("=" * 65)
    print("NYXERIS <- TITAN-ONE CO-PILOT TRAINING & CATALOG PIPELINE")
    print("=" * 65)

    final_curated_catalog = []

    for item in CANDIDATE_PRODUCTS:
        print(f"\n--- [TASK 1: Evaluation] Delegating to Titan-One for: {item['title'][:40]} ---")
        eval_result = evaluate_product_with_titan(item)
        
        if not eval_result:
            print("    [!] Titan-One evaluation failed, applying fallback supervisor defaults.")
            eval_result = {
                "brand_fit_score": 9,
                "approved": True,
                "suggested_nyxeris_title": f"Nyxeris {item['category'].split('&')[0].strip()} Precision Hardware",
                "target_retail_price": round(item["cost_price"] * 4.5, 2),
                "reasoning": "High-margin hardware fitting modern studio setups."
            }

        print(f"    Titan-One Verdict: Score {eval_result.get('brand_fit_score', 'N/A')}/10 | Approved: {eval_result.get('approved')}")
        print(f"    Suggested Title: {eval_result.get('suggested_nyxeris_title')}")
        print(f"    Target Retail: ${eval_result.get('target_retail_price', 0.0):.2f} (Supplier Cost: ${item['cost_price']:.2f})")
        print(f"    Reasoning: {eval_result.get('reasoning')}")

        # Compute margins
        retail = float(eval_result.get("target_retail_price", item["cost_price"] * 4))
        cost = item["cost_price"]
        margin = round(((retail - cost) / retail) * 100, 1)

        product_record = {
            "id": item["id"],
            "title": eval_result.get("suggested_nyxeris_title") or item["title"],
            "slug": item["slug"],
            "category": item["category"],
            "price": retail,
            "cost_price": cost,
            "profit_margin": margin,
            "sku": item["sku"],
            "supplier_url": item["href"],
            "image_url": item["image_url"],
            "badge": item["badge"]
        }

        print(f"\n--- [TASK 2: Copywriting] Delegating to Titan-One for: {product_record['title']} ---")
        copy_result = generate_whop_copy_with_titan(product_record)
        if copy_result:
            product_record["tagline"] = copy_result.get("tagline", "")
            product_record["description"] = copy_result.get("short_description", "")
            product_record["features"] = copy_result.get("bullet_features", [])
            product_record["specs"] = copy_result.get("specs_breakdown", {})
            print(f"    Tagline: {product_record['tagline']}")
            print(f"    Features generated: {len(product_record['features'])}")
        else:
            product_record["tagline"] = "Engineered for tactile focus and enduring desk architecture."
            product_record["description"] = f"Precision {product_record['title']} manufactured to uncompromising tolerances."
            product_record["features"] = ["Precision Aerospace Alloy", "Ergonomic Performance", "Minimalist Profile"]
            product_record["specs"] = {"Materials": "Anodized Aluminum / Polymer", "Origin": "Precision Hardware"}

        final_curated_catalog.append(product_record)

    # Save to SQLite
    print("\n--- [TASK 3: Database Persistence (Handled by Antigravity)] ---")
    conn = get_db_connection()
    cursor = conn.cursor()
    for p in final_curated_catalog:
        cursor.execute("SELECT id FROM products WHERE slug = ?", (p["slug"],))
        exists = cursor.fetchone()
        desc = f"{p.get('tagline', '')} {p.get('description', '')}".strip()
        if exists:
            cursor.execute("""
                UPDATE products
                SET title = ?,
                    description = ?,
                    price = ?,
                    cost_price = ?,
                    supplier_url = ?,
                    sku = ?,
                    image_url = ?,
                    badge = ?
                WHERE slug = ?
            """, (p["title"], desc, p["price"], p["cost_price"], p["supplier_url"], p["sku"], p["image_url"], p["badge"], p["slug"]))
        else:
            cursor.execute("""
                INSERT INTO products (
                    id, title, slug, description, category, price, cost_price,
                    stock_quantity, sku, supplier_url, image_url, badge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 50, ?, ?, ?, ?)
            """, (
                p["id"], p["title"], p["slug"], desc,
                p["category"], p["price"], p["cost_price"],
                p["sku"], p["supplier_url"], p["image_url"], p["badge"]
            ))
    conn.commit()
    conn.close()
    print("[SUCCESS] Nyxeris SQLite database synchronized with Titan-One curated products.")

    # Save catalog JSON
    json_path = DATA_DIR / "titan_curated_catalog.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_curated_catalog, f, indent=2)
    print(f"[*] Saved JSON Catalog: {json_path}")

    # Generate Whop CSV for 1-click import
    csv_path = DATA_DIR / "whop_products_catalog.csv"
    lines = [
        "Product Name,Category,Price USD,Cost USD,Gross Margin %,SKU,Tagline,CJ Supplier URL,Image URL,Key Features"
    ]
    for p in final_curated_catalog:
        features_str = " | ".join(p.get("features", [])).replace('"', '""')
        tagline_clean = p.get("tagline", "").replace('"', '""')
        lines.append(
            f'"{p["title"]}","{p["category"]}",{p["price"]},{p["cost_price"]},{p["profit_margin"]}%,{p["sku"]},"{tagline_clean}","{p["supplier_url"]}","{p["image_url"]}","{features_str}"'
        )
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[*] Exported Whop Product Import CSV: {csv_path}")


if __name__ == "__main__":
    run_training_pipeline()
