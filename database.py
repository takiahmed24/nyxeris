"""Database connection and initialization module for Nyxeris."""

import sqlite3
import json
import datetime
from pathlib import Path
from config import settings


def get_db_connection():
    """Returns a SQLite connection with dict-like row factory."""
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema and seeds initial physical products."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            compare_at_price REAL,
            cost_price REAL,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            sku TEXT UNIQUE NOT NULL,
            supplier_url TEXT,
            image_url TEXT NOT NULL,
            badge TEXT,
            specs TEXT,
            variants TEXT,
            whop_product_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Safe migration for whop_product_id and whop_checkout_url columns
    cursor.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cursor.fetchall()]
    if "whop_product_id" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN whop_product_id TEXT")
    if "whop_checkout_url" not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN whop_checkout_url TEXT")

    # Create Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT,
            shipping_address_line1 TEXT NOT NULL,
            shipping_address_line2 TEXT,
            shipping_city TEXT NOT NULL,
            shipping_state TEXT NOT NULL,
            shipping_postal_code TEXT NOT NULL,
            shipping_country TEXT NOT NULL,
            shipping_method TEXT NOT NULL,
            subtotal REAL NOT NULL,
            shipping_fee REAL NOT NULL,
            tax REAL NOT NULL,
            total_amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            payment_method TEXT NOT NULL DEFAULT 'Whop Payments',
            payment_status TEXT NOT NULL DEFAULT 'pending',
            whop_checkout_id TEXT,
            whop_payment_id TEXT,
            receipt_pdf_path TEXT,
            fulfillment_status TEXT NOT NULL DEFAULT 'unfulfilled',
            carrier TEXT,
            tracking_number TEXT,
            tracking_url TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Safe migration for packaging_tier, packaging_fee, and customer_id columns in orders
    cursor.execute("PRAGMA table_info(orders)")
    order_columns = [col[1] for col in cursor.fetchall()]
    if "packaging_tier" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN packaging_tier TEXT DEFAULT 'standard'")
    if "packaging_fee" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN packaging_fee REAL DEFAULT 0.0")
    if "customer_id" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN customer_id TEXT")

    # Create Customers table for store user authentication & accounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            country TEXT DEFAULT 'United States',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create Order Items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            product_title TEXT NOT NULL,
            variant_title TEXT,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            sku TEXT,
            image_url TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (order_id) ON DELETE CASCADE
        )
    """)

    # Create Store Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS store_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    conn.commit()

    # Seed default physical products if table is empty
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_products(conn)

    conn.close()


def seed_products(conn):
    """Populates store with premier physical items designed for dropshipping or own brand."""
    products = [
        {
            "id": "prod_lumina_pad",
            "title": "Lumina Matte Vegan-Leather Precision Desk Mat",
            "slug": "lumina-matte-desk-mat",
            "description": "Precision water-resistant desk mat handcrafted from dual-layer vegan obsidian leather with non-slip suede underside. Engineered for ultra-smooth gliding and tactile desktop aesthetics.",
            "category": "Workspace & Studio",
            "price": 49.00,
            "compare_at_price": 69.00,
            "cost_price": 14.50,
            "stock_quantity": 85,
            "sku": "NYX-DESK-LUM01",
            "supplier_url": "https://supplier.nyxeris.internal/sku/desk-pad-lumina",
            "image_url": "/static/images/products/nyxeris-lumina-desk-mat.jpg",
            "badge": "Bestseller",
            "specs": json.dumps({
                "Dimensions": "900mm x 400mm x 2.2mm",
                "Weight": "580g",
                "Material": "Dual-sided Hydrophobic Polyurethane Vegan Leather",
                "Guarantee": "30-Day Transit & Quality Guarantee"
            }),
            "variants": json.dumps([
                {"name": "Midnight Charcoal (XL)", "sku": "NYX-DESK-LUM01-MC", "in_stock": True},
                {"name": "Stealth Slate (XL)", "sku": "NYX-DESK-LUM01-SS", "in_stock": True}
            ])
        },
        {
            "id": "prod_obsidian_board",
            "title": "Apex-65 Magnetic HE Rapid-Trigger Mechanical Keyboard",
            "slug": "apex-65-he-keyboard",
            "description": "High-performance Hall Effect 65% CNC anodized aluminum mechanical keyboard. Rapid-trigger 0.1mm actuation, pre-lubed Gateron Jade magnetic switches, and per-key RGB backlighting with sound-dampening poron gasket structure.",
            "category": "Peripherals & Tech",
            "price": 179.00,
            "compare_at_price": 220.00,
            "cost_price": 68.00,
            "stock_quantity": 42,
            "sku": "NYX-KEY-APX65",
            "supplier_url": "https://supplier.nyxeris.internal/sku/keyboard-apex-65",
            "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80",
            "badge": "Signature",
            "specs": json.dumps({
                "Actuation": "0.1mm - 4.0mm Continuous Adjustable",
                "Polling Rate": "8000Hz Ultra-Low Latency",
                "Weight": "1450g CNC Billet Aluminum",
                "Switches": "Pre-lubed Gateron Magnetic Jade"
            }),
            "variants": json.dumps([
                {"name": "Anodized Charcoal / Stealth Dark", "sku": "NYX-KEY-APX65-DRK", "in_stock": True},
                {"name": "Space Gray / Frost White", "sku": "NYX-KEY-APX65-GRY", "in_stock": True}
            ])
        },
        {
            "id": "prod_apex_audio",
            "title": "Acoustic-1 Reference Studio Audio DAC & Headphone Amp",
            "slug": "acoustic-1-dac-amp",
            "description": "True balanced 32-bit/768kHz reference DAC and Class-A headphone amplifier. Dual ESS Sabre ES9038Q2M architecture inside a monolithic bead-blasted aluminum shell for zero electrical noise floor.",
            "category": "Peripherals & Tech",
            "price": 149.00,
            "compare_at_price": 185.00,
            "cost_price": 52.00,
            "stock_quantity": 30,
            "sku": "NYX-AUD-AC101",
            "supplier_url": "https://supplier.nyxeris.internal/sku/audio-dac-acoustic1",
            "image_url": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=800&auto=format&fit=crop&q=80",
            "badge": "Audiophile Grade",
            "specs": json.dumps({
                "Decoding": "PCM 32-bit/768kHz, Native DSD512",
                "Outputs": "4.4mm Pentaconn Balanced + 6.35mm Single-Ended",
                "Output Power": "1200mW @ 32 Ohms",
                "Distortion": "THD+N < 0.00015%"
            }),
            "variants": json.dumps([
                {"name": "Matte Obsidian", "sku": "NYX-AUD-AC101-OBS", "in_stock": True}
            ])
        },
        {
            "id": "prod_horizon_light",
            "title": "Horizon Pro Screen Ambient Asymmetric Light Bar",
            "slug": "horizon-pro-light-bar",
            "description": "Asymmetric optical monitor light bar with zero screen glare, touch-sensitive capacitive remote dial, and intelligent dynamic ambient back-glow. Supports Ra95 high CRI natural lighting with 2700K - 6500K stepless temperature control.",
            "category": "Workspace & Studio",
            "price": 89.00,
            "compare_at_price": 119.00,
            "cost_price": 26.00,
            "stock_quantity": 53,
            "sku": "NYX-LGT-HRZ01",
            "supplier_url": "https://supplier.nyxeris.internal/sku/screenbar-horizon",
            "image_url": "/static/images/products/nyxeris-horizon-screenbar-light.jpg",
            "badge": "Editor's Choice",
            "specs": json.dumps({
                "Illumination": "Asymmetric 45-degree Forward Optics",
                "Color Rendering": "Ra95 High CRI",
                "Power Input": "USB-C 5V/2A",
                "Mounting": "Counterweighted Clamp (Flat & Curved Monitors)"
            }),
            "variants": json.dumps([
                {"name": "Matte Charcoal Edition", "sku": "NYX-LGT-HRZ01-CHR", "in_stock": True}
            ])
        },
        {
            "id": "prod_pulse_dock",
            "title": "Matrix 3-in-1 Foldable Qi2 MagSafe Fast Power Station",
            "slug": "matrix-3in1-magsafe-station",
            "description": "Aerospace-grade billet aluminum fast wireless charging station for Phone, Watch, and Earbuds. Delivers certified 15W Qi2 fast magnetic alignment in an ultra-compact pocket-fold architecture.",
            "category": "Smart Gear & Power",
            "price": 95.00,
            "compare_at_price": 125.00,
            "cost_price": 29.50,
            "stock_quantity": 78,
            "sku": "NYX-PWR-MTX31",
            "supplier_url": "https://supplier.nyxeris.internal/sku/magsafe-3in1-matrix",
            "image_url": "/static/images/products/nyxeris-matrix-magsafe-station.jpg",
            "badge": "Qi2 Certified",
            "specs": json.dumps({
                "Output": "15W Magnetic Phone + 5W Watch + 5W Audio",
                "Chassis": "Billet CNC Aluminum & Frosted Glass Face",
                "Dimensions": "68mm x 68mm x 22mm (Folded)",
                "Weight": "210g"
            }),
            "variants": json.dumps([
                {"name": "Graphite Dark", "sku": "NYX-PWR-MTX31-GPH", "in_stock": True},
                {"name": "Titanium Frost", "sku": "NYX-PWR-MTX31-TTN", "in_stock": True}
            ])
        },
        {
            "id": "prod_edc_tool",
            "title": "Vektor Grade-5 Titanium Precision Pocket Multi-Tool",
            "slug": "vektor-titanium-edc-tool",
            "description": "Precision EDM-wire-cut Grade 5 Titanium pocket pry-bar, bottle opener, hex wrench array, metric ruler, and concealed tungsten carbide glass-breaker stylus. Finished with a durable diamond-like carbon (DLC) coating.",
            "category": "Accessories & EDC",
            "price": 55.00,
            "compare_at_price": 75.00,
            "cost_price": 16.00,
            "stock_quantity": 110,
            "sku": "NYX-EDC-VEK01",
            "supplier_url": "https://supplier.nyxeris.internal/sku/titanium-tool-vektor",
            "image_url": "/static/images/products/nyxeris-vektor-titanium-tool.jpg",
            "badge": "Grade 5 Titanium",
            "specs": json.dumps({
                "Material": "Ti-6Al-4V Grade 5 Aerospace Titanium",
                "Coating": "DLC (Diamond-Like Carbon) Matte Finish",
                "Functions": "12-in-1 Integrated Modular EDC Architecture",
                "Weight": "48g"
            }),
            "variants": json.dumps([
                {"name": "DLC Matte Black", "sku": "NYX-EDC-VEK01-DLC", "in_stock": True},
                {"name": "Raw Stonewashed Titanium", "sku": "NYX-EDC-VEK01-STW", "in_stock": True}
            ])
        }
    ]

    cursor = conn.cursor()
    for p in products:
        cursor.execute("""
            INSERT INTO products (
                id, title, slug, description, category, price, compare_at_price,
                cost_price, stock_quantity, sku, supplier_url, image_url, badge,
                specs, variants
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["id"], p["title"], p["slug"], p["description"], p["category"],
            p["price"], p["compare_at_price"], p["cost_price"], p["stock_quantity"],
            p["sku"], p["supplier_url"], p["image_url"], p["badge"],
            p["specs"], p["variants"]
        ))
    conn.commit()


# Run initialization on import if not existing
init_db()
