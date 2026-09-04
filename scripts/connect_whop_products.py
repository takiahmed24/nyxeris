import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
import json
import csv
from pathlib import Path
import config

CSV_FILE = Path("data/whop_ai_generated_batch.csv")
MAPPING_FILE = Path("data/whop_id_mapping.json")
CATALOG_JSON = Path("data/cj_200_products.json")

def connect_whop_ids():
    mapping = {}
    
    # 1. Read CSV if available
    if CSV_FILE.exists():
        print(f"[*] Reading Whop IDs from {CSV_FILE}...")
        with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                internal_id = row.get("internal_id", "").strip()
                whop_id = row.get("whop_product_id", "").strip()
                whop_url = row.get("whop_checkout_url", "").strip()
                if internal_id and whop_id:
                    mapping[internal_id] = {
                        "whop_product_id": whop_id,
                        "whop_checkout_url": whop_url or f"https://whop.com/checkout/{whop_id}"
                    }
    elif MAPPING_FILE.exists():
        print(f"[*] Reading Whop IDs from {MAPPING_FILE}...")
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            raw_map = json.load(f)
            for pid, data in raw_map.items():
                if isinstance(data, str):
                    mapping[pid] = {
                        "whop_product_id": data,
                        "whop_checkout_url": f"https://whop.com/checkout/{data}" if not data.startswith("http") else data
                    }
                elif isinstance(data, dict):
                    whop_id = data.get("whop_product_id") or data.get("id") or ""
                    whop_url = data.get("whop_checkout_url") or data.get("url") or f"https://whop.com/checkout/{whop_id}"
                    if whop_id:
                        mapping[pid] = {"whop_product_id": whop_id, "whop_checkout_url": whop_url}
    else:
        print(f"[!] Neither {CSV_FILE} nor {MAPPING_FILE} found.")
        return

    # 2. Update SQLite database
    conn = sqlite3.connect(config.settings.DATABASE_PATH)
    c = conn.cursor()
    
    connected_count = 0
    not_found = []
    
    for pid, data in mapping.items():
        whop_id = data["whop_product_id"]
        whop_url = data["whop_checkout_url"]
        
        c.execute("""
            UPDATE products 
            SET whop_product_id = ?, whop_checkout_url = ?
            WHERE id = ?
        """, (whop_id, whop_url, pid))
        
        if c.rowcount > 0:
            connected_count += 1
        else:
            not_found.append(pid)
            
    conn.commit()
    conn.close()
    
    # 3. Update catalog JSON file
    if CATALOG_JSON.exists():
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        for item in catalog:
            iid = item.get("id")
            if iid in mapping:
                item["whop_product_id"] = mapping[iid]["whop_product_id"]
                item["whop_checkout_url"] = mapping[iid]["whop_checkout_url"]
        with open(CATALOG_JSON, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
            
    # 4. Save clean mapping JSON
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)
        
    print(f"[SUCCESS] Successfully linked {connected_count} products with Whop Checkout URLs!")
    if not_found:
        print(f"[NOTE] {len(not_found)} IDs not matched in products table: {not_found[:5]}")

if __name__ == "__main__":
    connect_whop_ids()
