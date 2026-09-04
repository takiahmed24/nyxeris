import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
import json
from pathlib import Path
import config

MAPPING_FILE = Path("data/whop_id_mapping.json")

def connect_whop_ids():
    if not MAPPING_FILE.exists():
        print(f"[!] {MAPPING_FILE} not found. Please create it or use data/whop_mapping_template.json")
        return
    
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        mapping = json.load(f)
        
    conn = sqlite3.connect(config.settings.DATABASE_PATH)
    c = conn.cursor()
    
    connected_count = 0
    for pid, data in mapping.items():
        whop_id = ""
        whop_url = ""
        if isinstance(data, str):
            whop_id = data
            whop_url = f"https://whop.com/checkout/{data}" if not data.startswith("http") else data
        elif isinstance(data, dict):
            whop_id = data.get("whop_product_id") or data.get("id") or ""
            whop_url = data.get("whop_checkout_url") or data.get("url") or ""
            if whop_id and not whop_url:
                whop_url = f"https://whop.com/checkout/{whop_id}"
                
        if whop_id:
            c.execute("""
                UPDATE products 
                SET whop_product_id = ?, whop_checkout_url = ?
                WHERE id = ?
            """, (whop_id, whop_url, pid))
            connected_count += 1
            
    conn.commit()
    conn.close()
    print(f"[SUCCESS] Successfully connected {connected_count} Whop product IDs to Nyxeris database!")

if __name__ == "__main__":
    connect_whop_ids()
