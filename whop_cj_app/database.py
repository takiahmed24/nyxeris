"""Authoritative Database Layer for CJ Dropshipping for Whop SaaS Bridge."""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from config import DB_PATH

logger = logging.getLogger("whop_cj.db")

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory and WAL mode for robust concurrency."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
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
        plan_tier TEXT DEFAULT 'Creator',
        plan_price REAL DEFAULT 5.00,
        plan_interval TEXT DEFAULT 'monthly',
        payment_method TEXT DEFAULT 'whop_balance',
        whop_balance REAL DEFAULT 432.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Safe column migrations for existing SQLite databases
    billing_cols = [
        ("plan_tier", "TEXT DEFAULT 'Creator'"),
        ("plan_price", "REAL DEFAULT 5.00"),
        ("plan_interval", "TEXT DEFAULT 'monthly'"),
        ("payment_method", "TEXT DEFAULT 'whop_balance'"),
        ("whop_balance", "REAL DEFAULT 432.00")
    ]
    for col_name, col_def in billing_cols:
        try:
            c.execute(f"ALTER TABLE merchant_settings ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass

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

    # Multi-tenant Sourcing Requests table
    c.execute("""
    CREATE TABLE IF NOT EXISTS sourcing_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL DEFAULT 'biz_ea3gy6pg50A7px',
        product_name TEXT NOT NULL,
        target_price REAL DEFAULT 0.0,
        image_url TEXT DEFAULT '',
        details TEXT DEFAULT '',
        status TEXT DEFAULT 'Pending Review',
        cj_source_url TEXT DEFAULT '',
        quoted_price REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Multi-tenant Notifications table
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL DEFAULT 'biz_ea3gy6pg50A7px',
        type TEXT DEFAULT 'system',
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        time_ago TEXT DEFAULT 'Just now',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Multi-tenant Billing & Wallet table
    c.execute("""
    CREATE TABLE IF NOT EXISTS billing_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL DEFAULT 'biz_ea3gy6pg50A7px',
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'completed',
        reference_id TEXT DEFAULT '',
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

    # Seed realistic design system orders if table is empty or sparse
    c.execute("SELECT COUNT(*) FROM orders WHERE company_id = ?", (DEFAULT_COMPANY_ID,))
    if c.fetchone()[0] == 0:
        sample_orders = [
            (DEFAULT_COMPANY_ID, "WHOP-10024", "Alex R.", "alex.r@example.com", "+1 555-234-9812", "US", 
             json.dumps({"line1": "742 Evergreen Terrace", "city": "Springfield", "state": "OR", "postal_code": "97477", "country": "United States"}),
             json.dumps([{"whop_title": "Minimalist Hoodie", "variant": "Gray / L", "quantity": 1, "unit_price": 18.50}]),
             18.50, "USD", "paid", "CJ-ORD-98821", "fulfilled", "1ZC920491029348F2", "UPS", "https://www.ups.com/track?tracknum=1ZC920491029348F2", 1, ""),
            (DEFAULT_COMPANY_ID, "WHOP-10023", "Jessica M.", "jessica.m@example.com", "+1 555-891-3411", "US", 
             json.dumps({"line1": "104 West 40th St", "city": "New York", "state": "NY", "postal_code": "10018", "country": "United States"}),
             json.dumps([{"whop_title": "Wireless Earbuds", "variant": "Matte White", "quantity": 1, "unit_price": 24.90}]),
             24.90, "USD", "paid", "CJ-ORD-98822", "tracking_generated", "YT7391028349KDL", "YunExpress", "https://www.yuntrack.com/parcelTracking?nums=YT7391028349KDL", 1, ""),
            (DEFAULT_COMPANY_ID, "WHOP-10022", "Daniel K.", "daniel.k@example.com", "+44 20 7946 0912", "GB", 
             json.dumps({"line1": "221B Baker St", "city": "London", "state": "England", "postal_code": "NW1 6XE", "country": "United Kingdom"}),
             json.dumps([{"whop_title": "Smart Watch", "variant": "Midnight Black", "quantity": 1, "unit_price": 32.00}]),
             32.00, "USD", "paid", "CJ-ORD-98823", "synced", "LV9283746193H7Q", "Royal Mail", "https://www.royalmail.com/track-your-item#/tracking-results/LV9283746193H7Q", 1, ""),
            (DEFAULT_COMPANY_ID, "WHOP-10021", "Sarah T.", "sarah.t@example.com", "+1 555-762-4419", "CA", 
             json.dumps({"line1": "300 Queen St W", "city": "Toronto", "state": "ON", "postal_code": "M5V 2A2", "country": "Canada"}),
             json.dumps([{"whop_title": "Phone Case", "variant": "Matte Frosted", "quantity": 1, "unit_price": 12.00}]),
             12.00, "USD", "paid", "CJ-ORD-98824", "fulfilled", "1ZV9283401926DP9", "Canada Post", "https://www.canadapost-postescanada.ca/track-reperage/en#/result_list?tracking_number=1ZV9283401926DP9", 1, ""),
            (DEFAULT_COMPANY_ID, "WHOP-10020", "Michael B.", "michael.b@example.com", "+61 2 9374 4000", "AU", 
             json.dumps({"line1": "48 Pirrama Rd", "city": "Pyrmont", "state": "NSW", "postal_code": "2009", "country": "Australia"}),
             json.dumps([{"whop_title": "Desk Lamp", "variant": "Warm Aluminum", "quantity": 1, "unit_price": 28.50}]),
             28.50, "USD", "paid", "CJ-ORD-98825", "tracking_generated", "YT2837461928PLM", "YunExpress", "https://www.yuntrack.com/parcelTracking?nums=YT2837461928PLM", 1, "")
        ]
        c.executemany("""
            INSERT INTO orders (
                company_id, whop_order_id, customer_name, customer_email, customer_phone,
                shipping_country, shipping_address_json, items_json, total_amount, currency,
                whop_payment_status, cj_order_id, cj_order_status, tracking_number,
                tracking_carrier, tracking_url, whop_fulfilled, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_orders)

    # Seed sample notifications matching Screen 09
    c.execute("SELECT COUNT(*) FROM notifications WHERE company_id = ?", (DEFAULT_COMPANY_ID,))
    if c.fetchone()[0] == 0:
        sample_notifs = [
            (DEFAULT_COMPANY_ID, "orders", "Order Fulfilled", "#100245 has been shipped via UPS with active tracking.", "2m ago", 0),
            (DEFAULT_COMPANY_ID, "orders", "New Order", "#100246 received from United States ($38.50).", "12m ago", 0),
            (DEFAULT_COMPANY_ID, "products", "Low Stock Alert", "Wireless Earbuds (Matte White) is running low in CJ US Warehouse.", "1h ago", 0),
            (DEFAULT_COMPANY_ID, "system", "Product Sync Complete", "12 products and 34 variants synced to Whop store catalog.", "2h ago", 1),
            (DEFAULT_COMPANY_ID, "system", "Payout Processed", "$432.00 has been transferred to your connected balance.", "1d ago", 1)
        ]
        c.executemany("""
            INSERT INTO notifications (company_id, type, title, message, time_ago, is_read)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_notifs)

    # Seed sample sourcing requests matching Screen 07
    c.execute("SELECT COUNT(*) FROM sourcing_requests WHERE company_id = ?", (DEFAULT_COMPANY_ID,))
    if c.fetchone()[0] == 0:
        sample_sourcing = [
            (DEFAULT_COMPANY_ID, "Custom Matte Phone Case", 4.50, "https://images.unsplash.com/photo-1586953208448-b95a79798f07?w=600", "Matte silicone finish with anti-scratch inner microfiber lining. MagSafe ring built-in.", "Quoted", "https://cjdropshipping.com/product/custom-case", 4.20),
            (DEFAULT_COMPANY_ID, "Oversized Heavyweight Hoodie", 14.00, "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600", "450 GSM French Terry Cotton, custom embroidered chest logo, vintage wash.", "Reviewing", "", 0.0),
            (DEFAULT_COMPANY_ID, "Titanium Wireless Smart Ring", 22.00, "https://images.unsplash.com/photo-1605100804763-247f67b3557e?w=600", "Health monitoring smart ring with heart rate & sleep tracking. IP68 waterproof.", "Sourced", "https://cjdropshipping.com/product/smart-ring", 19.80)
        ]
        c.executemany("""
            INSERT INTO sourcing_requests (company_id, product_name, target_price, image_url, details, status, cj_source_url, quoted_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_sourcing)

    # Seed sample billing transactions
    c.execute("SELECT COUNT(*) FROM billing_transactions WHERE company_id = ?", (DEFAULT_COMPANY_ID,))
    if c.fetchone()[0] == 0:
        sample_txs = [
            (DEFAULT_COMPANY_ID, "recharge", 500.00, "Auto-Recharge - Connected Visa ending 4242", "completed", "TX-9901"),
            (DEFAULT_COMPANY_ID, "fulfillment", -98.40, "CJ Fulfillment Batch #10020 - #10024", "completed", "CJ-BATCH-882"),
            (DEFAULT_COMPANY_ID, "sourcing", -25.00, "Custom Sample Inspection Fee - Titanium Ring", "completed", "SR-SAMPLE-01"),
            (DEFAULT_COMPANY_ID, "fulfillment", -64.20, "CJ Fulfillment Batch #10015 - #10019", "completed", "CJ-BATCH-879")
        ]
        c.executemany("""
            INSERT INTO billing_transactions (company_id, transaction_type, amount, description, status, reference_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_txs)

    # Ensure default sample SKU mappings exist for primary company
    c.execute("SELECT COUNT(*) FROM sku_mappings WHERE company_id = ?", (DEFAULT_COMPANY_ID,))
    if c.fetchone()[0] == 0:
        sample_mappings = [
            (DEFAULT_COMPANY_ID, "prod_nyx_hoodie", "Minimalist Hoodie", "Gray / L", "NYX-HOD-GRY", "CJ-APP-8801", "VID-011", "CJ-HOD-GRY-L", "Comfort Heavyweight Minimalist Unisex Hoodie", 14.20),
            (DEFAULT_COMPANY_ID, "prod_nyx_earbuds", "Wireless Earbuds", "Matte White", "NYX-EAR-WHT", "CJ-AUD-4421", "VID-012", "CJ-EAR-ANC-WHT", "True Wireless Active Noise Cancelling Earbuds", 12.80),
            (DEFAULT_COMPANY_ID, "prod_nyx_watch", "Smart Watch", "Midnight Black", "NYX-WCH-BLK", "CJ-WAT-7712", "VID-013", "CJ-WCH-PRO-BLK", "Waterproof Smart Fitness Health Tracker Watch", 16.30),
            (DEFAULT_COMPANY_ID, "prod_nyx_lamp", "LED Desk Lamp", "Warm Aluminum", "NYX-LMP-ALM", "CJ-LGT-3301", "VID-014", "CJ-LMP-SLM-ALM", "Minimalist Aluminum Eye-Care LED Desk Lamp", 8.50),
            (DEFAULT_COMPANY_ID, "prod_nyx_case", "Phone Case", "Matte Frosted", "NYX-PHN-MAT", "CJ-ACC-9921", "VID-015", "CJ-CSE-MAG-CLR", "Impact Shockproof Magnetic Slim Phone Case", 4.50),
            (DEFAULT_COMPANY_ID, "prod_nyx_mug", "Custom Ceramic Mug", "Ceramic White", "NYX-MUG-WHT", "CJ-MUG-1102", "VID-016", "CJ-MUG-350ML", "Sublimation Ceramic Minimalist Coffee Mug", 3.20)
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

def get_sourcing_requests(company_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all sourcing requests for the merchant."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sourcing_requests WHERE company_id = ? ORDER BY id DESC", (active_cid,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_sourcing_request(company_id: str, product_name: str, target_price: float, image_url: str = "", details: str = "") -> int:
    """Inserts a new merchant custom sourcing request."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO sourcing_requests (company_id, product_name, target_price, image_url, details, status)
        VALUES (?, ?, ?, ?, ?, 'Pending Review')
    """, (active_cid, product_name, target_price, image_url, details))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_notifications(company_id: Optional[str] = None, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves notifications scoped to merchant, optionally filtered by type."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    conn = get_db_connection()
    c = conn.cursor()
    if filter_type and filter_type.lower() != "all":
        c.execute("SELECT * FROM notifications WHERE company_id = ? AND type = ? ORDER BY id DESC", (active_cid, filter_type.lower()))
    else:
        c.execute("SELECT * FROM notifications WHERE company_id = ? ORDER BY id DESC", (active_cid,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def mark_notifications_read(company_id: Optional[str] = None):
    """Marks all notifications as read for active merchant."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE notifications SET is_read = 1 WHERE company_id = ?", (active_cid,))
    conn.commit()
    conn.close()

def get_billing_transactions(company_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves billing transactions and ledger items for merchant."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM billing_transactions WHERE company_id = ? ORDER BY id DESC", (active_cid,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def add_billing_transaction(company_id: str, tx_type: str, amount: float, description: str, ref_id: str = ""):
    """Inserts a billing or wallet transaction."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO billing_transactions (company_id, transaction_type, amount, description, status, reference_id)
        VALUES (?, ?, ?, ?, 'completed', ?)
    """, (active_cid, tx_type, amount, description, ref_id))
    conn.commit()
    conn.close()

def add_notification(company_id: str, notif_type: str, title: str, message: str, time_ago: str = "Just now"):
    """Inserts a new notification for active merchant."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO notifications (company_id, type, title, message, time_ago, is_read)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (active_cid, notif_type, title, message, time_ago))
    conn.commit()
    conn.close()

def update_billing_settings(
    company_id: Optional[str] = None,
    plan_tier: Optional[str] = None,
    plan_price: Optional[float] = None,
    plan_interval: Optional[str] = None,
    payment_method: Optional[str] = None,
    balance_delta: float = 0.0
):
    """Updates merchant subscription tier, payment preference, or wallet balance."""
    active_cid = company_id.strip() if company_id and company_id.strip() else DEFAULT_COMPANY_ID
    get_or_create_merchant(active_cid)
    conn = get_db_connection()
    c = conn.cursor()
    updates = []
    params = []
    if plan_tier is not None:
        updates.append("plan_tier = ?")
        params.append(plan_tier)
    if plan_price is not None:
        updates.append("plan_price = ?")
        params.append(plan_price)
    if plan_interval is not None:
        updates.append("plan_interval = ?")
        params.append(plan_interval)
    if payment_method is not None:
        updates.append("payment_method = ?")
        params.append(payment_method)
    if balance_delta != 0.0:
        updates.append("whop_balance = MAX(0.0, COALESCE(whop_balance, 432.00) + ?)")
        params.append(balance_delta)
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        sql = f"UPDATE merchant_settings SET {', '.join(updates)} WHERE company_id = ?"
        params.append(active_cid)
        c.execute(sql, params)
        conn.commit()
    conn.close()

# Auto-initialize when module is imported
init_db()

