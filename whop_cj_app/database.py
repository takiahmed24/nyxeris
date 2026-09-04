"""Authoritative Database Layer for CJ Dropshipping for Whop SaaS Bridge."""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from config import DB_PATH

logger = logging.getLogger("whop_cj.db")

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

DEFAULT_COMPANY_ID = "biz_ea3gy6pg50A7px"

def init_db():
    """Initializes the required database schema with multi-tenant company isolation."""
    conn = get_db_connection()
    c = conn.cursor()

    # Multi-merchant / multi-tenant settings table
    c.execute("""
    CREATE TABLE IF NOT EXISTS merchant_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT UNIQUE NOT NULL,
        account_name TEXT DEFAULT 'Whop Merchant Store',
        cj_email TEXT DEFAULT '',
        cj_api_key TEXT DEFAULT '',
        cj_access_token TEXT DEFAULT '',
        cj_token_expiry TEXT DEFAULT '',
        whop_api_key TEXT DEFAULT '',
        whop_webhook_secret TEXT DEFAULT '',
        auto_order_enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Multi-tenant SKU / Product Mapping table
    c.execute("""
    CREATE TABLE IF NOT EXISTS sku_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL DEFAULT 'biz_ea3gy6pg50A7px',
        whop_product_id TEXT NOT NULL,
        whop_product_title TEXT NOT NULL,
        whop_variant_title TEXT DEFAULT 'Standard',
        whop_sku TEXT DEFAULT '',
        cj_product_id TEXT NOT NULL,
        cj_variant_id TEXT DEFAULT '',
        cj_variant_sku TEXT NOT NULL,
        cj_product_title TEXT NOT NULL,
        cj_estimated_cost REAL DEFAULT 0.0,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, whop_product_id, whop_variant_title)
    );
    """)

    # Multi-tenant Synced Orders table
    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL DEFAULT 'biz_ea3gy6pg50A7px',
        whop_order_id TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT DEFAULT '',
        shipping_country TEXT NOT NULL,
        shipping_address_json TEXT NOT NULL,
        items_json TEXT NOT NULL,
        total_amount REAL DEFAULT 0.0,
        currency TEXT DEFAULT 'USD',
        whop_payment_status TEXT DEFAULT 'paid',
        cj_order_id TEXT DEFAULT '',
        cj_order_status TEXT DEFAULT 'pending',
        tracking_number TEXT DEFAULT '',
        tracking_carrier TEXT DEFAULT '',
        tracking_url TEXT DEFAULT '',
        whop_fulfilled INTEGER DEFAULT 0,
        last_error TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Multi-tenant Audit & Sync Activity Logs
    c.execute("""
    CREATE TABLE IF NOT EXISTS sync_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT DEFAULT 'biz_ea3gy6pg50A7px',
        order_id TEXT DEFAULT '',
        event_type TEXT NOT NULL,
        status TEXT NOT NULL,
        message TEXT NOT NULL,
        payload_json TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed default primary company if empty
    c.execute("SELECT COUNT(*) FROM merchant_settings WHERE company_id = ?", (DEFAULT_COMPANY_ID,))
    if c.fetchone()[0] == 0:
        c.execute("""
        INSERT INTO merchant_settings (company_id, account_name) 
        VALUES (?, 'Nyxeris Store')
        """, (DEFAULT_COMPANY_ID,))

    # Ensure default sample SKU mappings exist for primary company
    c.execute("SELECT COUNT(*) FROM sku_mappings WHERE company_id = ?", (DEFAULT_COMPANY_ID,))
    if c.fetchone()[0] == 0:
        sample_mappings = [
            (DEFAULT_COMPANY_ID, "prod_nyx_screenbar", "Nyxeris Horizon Pro ScreenBar Light", "Standard", "NYX-BAR-STD", "CJ-LIGHT-9901", "VID-001", "CJ-BAR-PRO-BLK", "Smart Ambient Monitor Bar Light", 18.50),
            (DEFAULT_COMPANY_ID, "prod_nyx_magsafe", "Nyxeris Matrix 3-in-1 MagSafe Station", "Standard", "NYX-MAG-STD", "CJ-CHG-4412", "VID-002", "CJ-MAG-FOLD-SLV", "3-in-1 Foldable Magnetic Wireless Charger", 22.00),
            (DEFAULT_COMPANY_ID, "prod_nyx_deskmat", "Nyxeris Lumina Matte Leather Desk Mat", "Midnight Black", "NYX-MAT-BLK", "CJ-MAT-7703", "VID-003", "CJ-LEATH-MAT-80", "Waterproof Dual-Sided Vegan Leather Desk Mat", 9.80)
        ]
        c.executemany("""
            INSERT INTO sku_mappings (
                company_id, whop_product_id, whop_product_title, whop_variant_title, whop_sku,
                cj_product_id, cj_variant_id, cj_variant_sku, cj_product_title, cj_estimated_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_mappings)

    conn.commit()
    conn.close()
    logger.info("Database schema initialized with multi-tenant company isolation.")

def get_or_create_merchant(company_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves or registers a new merchant workspace by Whop Company ID."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM merchant_settings WHERE company_id = ?", (active_cid,))
    row = c.fetchone()
    if not row:
        # Create new merchant workspace for this newly installed company
        c.execute("""
            INSERT INTO merchant_settings (company_id, account_name)
            VALUES (?, ?)
        """, (active_cid, f"Store {active_cid[:10]}"))
        conn.commit()
        c.execute("SELECT * FROM merchant_settings WHERE company_id = ?", (active_cid,))
        row = c.fetchone()
    conn.close()
    return dict(row)

def get_settings(company_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves settings for a specific merchant workspace."""
    return get_or_create_merchant(company_id)

def list_merchants() -> List[Dict[str, Any]]:
    """Returns all merchant workspaces connected to this SaaS instance."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT company_id, account_name, created_at, (cj_api_key != '') as cj_connected FROM merchant_settings ORDER BY id ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def update_settings(data: Dict[str, Any], company_id: Optional[str] = None):
    """Updates settings for a specific merchant workspace."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    # Ensure merchant exists
    get_or_create_merchant(active_cid)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE merchant_settings
        SET cj_email = ?,
            cj_api_key = ?,
            cj_access_token = ?,
            cj_token_expiry = ?,
            whop_api_key = ?,
            whop_webhook_secret = ?,
            auto_order_enabled = ?,
            account_name = COALESCE(NULLIF(?, ''), account_name),
            updated_at = CURRENT_TIMESTAMP
        WHERE company_id = ?
    """, (
        data.get("cj_email", ""),
        data.get("cj_api_key", ""),
        data.get("cj_access_token", ""),
        data.get("cj_token_expiry", ""),
        data.get("whop_api_key", ""),
        data.get("whop_webhook_secret", ""),
        1 if data.get("auto_order_enabled", True) else 0,
        data.get("account_name", ""),
        active_cid
    ))
    conn.commit()
    conn.close()

def log_event(event_type: str, status: str, message: str, order_id: str = "", payload: Any = None, company_id: str = DEFAULT_COMPANY_ID):
    """Inserts a structured sync log entry scoped to a company."""
    conn = get_db_connection()
    c = conn.cursor()
    payload_str = json.dumps(payload) if payload else ""
    c.execute("""
        INSERT INTO sync_logs (company_id, order_id, event_type, status, message, payload_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (company_id, order_id, event_type, status, message, payload_str))
    conn.commit()
    conn.close()

# Auto-initialize when module is imported
init_db()
