import json
import sqlite3
from pathlib import Path

BASE_DIR = Path("C:/Nyxeris")
DB_PATH = BASE_DIR / "data" / "nyxeris.db"
MAP_PATH = BASE_DIR / "data" / "whop_product_ids.json"

WHOP_MAP = {
    "nyxeris-horizon-screenbar-light": "prod_AvrTlUnUF27GJ",
    "nyxeris-matrix-magsafe-station": "prod_P9kPPBuaT0ZWA",
    "nyxeris-lumina-desk-mat": "prod_YSZWBGFLqSOpT",
    "nyxeris-vektor-titanium-tool": "prod_XK5F2nTIcRPif"
}

def sync_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for slug, w_id in WHOP_MAP.items():
        c.execute("UPDATE products SET whop_product_id = ? WHERE slug = ?", (w_id, slug))
        print(f"[OK] Updated {slug} -> {w_id}")
    conn.commit()
    conn.close()

    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(WHOP_MAP, f, indent=2)
    print(f"[*] Saved mapping to {MAP_PATH}")

if __name__ == "__main__":
    sync_ids()
