import json
import re
from pathlib import Path
import sys

BASE_DIR = Path("C:/Nyxeris")
sys.path.insert(0, str(BASE_DIR))

from database import get_db_connection

def clean_text(text):
    if not text:
        return ""
    # Strip html tags and angle brackets
    text = re.sub(r'<[^>]*>', '', text)
    return text.strip()

def main():
    json_path = BASE_DIR / "data" / "titan_curated_catalog.json"
    with open(json_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    for item in catalog:
        item["tagline"] = clean_text(item.get("tagline", ""))
        item["description"] = clean_text(item.get("description", ""))
        item["features"] = [clean_text(f) for f in item.get("features", [])]
        if "specs" in item:
            for k in item["specs"]:
                item["specs"][k] = clean_text(item["specs"][k])

    # Save cleaned JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

    # Sync to SQLite
    conn = get_db_connection()
    c = conn.cursor()
    for item in catalog:
        full_desc = f"{item['tagline']} {item['description']}".strip()
        c.execute("""
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
        """, (
            item["title"], full_desc, item["price"], item["cost_price"],
            item["supplier_url"], item["sku"], item["image_url"], item["badge"],
            item["slug"]
        ))
    conn.commit()
    conn.close()

    # Export Whop CSV
    csv_path = BASE_DIR / "data" / "whop_products_catalog.csv"
    lines = [
        "Product Name,Category,Price USD,Cost USD,Gross Margin %,SKU,Tagline,CJ Supplier URL,Image URL,Key Features"
    ]
    for p in catalog:
        features_str = " | ".join(p.get("features", [])).replace('"', '""')
        tagline_clean = p.get("tagline", "").replace('"', '""')
        lines.append(
            f'"{p["title"]}","{p["category"]}",{p["price"]},{p["cost_price"]},{p["profit_margin"]}%,{p["sku"]},"{tagline_clean}","{p["supplier_url"]}","{p["image_url"]}","{features_str}"'
        )
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("[SUCCESS] Catalog cleaned and synchronized cleanly.")

if __name__ == "__main__":
    main()
