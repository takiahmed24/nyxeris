# Autonomous Whop Catalog Sync Engine for Nyxeris
# Learned from Whop API pipeline & assistant execution

import sys
import os
import csv
import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "nyxeris.db"
MAPPING_JSON = BASE_DIR / "data" / "whop_id_mapping.json"
CATALOG_CSV = BASE_DIR / "data" / "whop_1000_products_catalog.csv"
CATALOG_JSON = BASE_DIR / "data" / "nyxeris_1000_catalog.json"

MAX_TITLE_LENGTH = 80  # Hard Whop API constraint learned from live execution
DEFAULT_BATCH_SIZE = 125
POLLING_INTERVAL = 2.0


def sanitize_whop_title(title: str) -> str:
    """Enforces Whop API 80-character title limit."""
    clean = title.strip()
    if len(clean) > MAX_TITLE_LENGTH:
        return clean[:MAX_TITLE_LENGTH].rstrip()
    return clean


def apply_mapping_csv(csv_path: Path) -> int:
    """Ingests a Whop mapping CSV and syncs all products in SQLite nyxeris.db, JSON, and CSVs."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Mapping CSV not found at: {csv_path}")

    mapping = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            iid = row.get("internal_id", "").strip()
            if iid:
                mapping[iid] = {
                    "whop_product_id": row.get("whop_product_id", "").strip(),
                    "whop_plan_id": row.get("plan_id", "").strip(),
                    "whop_checkout_url": row.get("whop_checkout_url", "").strip(),
                    "image_attached": row.get("image_attached", "").strip().lower() == "true"
                }

    # 1. Update SQLite
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    updated = 0
    for iid, data in mapping.items():
        c.execute(
            "UPDATE products SET whop_product_id = ?, whop_checkout_url = ? WHERE id = ?",
            (data["whop_product_id"], data["whop_checkout_url"], iid)
        )
        if c.rowcount > 0:
            updated += 1
    conn.commit()
    conn.close()

    # 2. Update mapping JSON
    with open(MAPPING_JSON, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)

    # 3. Update nyxeris_1000_catalog.json
    if CATALOG_JSON.exists():
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            cat = json.load(f)
        for p in cat:
            pid = p.get("id")
            if pid in mapping:
                p["whop_product_id"] = mapping[pid]["whop_product_id"]
                p["whop_checkout_url"] = mapping[pid]["whop_checkout_url"]
        with open(CATALOG_JSON, "w", encoding="utf-8") as f:
            json.dump(cat, f, indent=2)

    # 4. Update whop_1000_products_catalog.csv
    if CATALOG_CSV.exists():
        rows = []
        with open(CATALOG_CSV, "r", encoding="utf-8-sig", newline="") as f:
            rdr = csv.DictReader(f)
            fieldnames = rdr.fieldnames
            for r in rdr:
                pid = r.get("Internal ID")
                if pid in mapping:
                    r["Whop Product ID"] = mapping[pid]["whop_product_id"]
                    r["Whop Checkout URL"] = mapping[pid]["whop_checkout_url"]
                rows.append(r)
        with open(CATALOG_CSV, "w", encoding="utf-8", newline="") as f:
            wtr = csv.DictWriter(f, fieldnames=fieldnames)
            wtr.writeheader()
            wtr.writerows(rows)

    return updated


if __name__ == "__main__":
    final_csv = BASE_DIR / "data" / "nyxeris_full_1024_catalog_mapping_FINAL.csv"
    if final_csv.exists():
        count = apply_mapping_csv(final_csv)
        print(f"[+] Successfully synchronized {count} products with real Whop IDs.")
    else:
        print("[!] Final CSV not found.")
