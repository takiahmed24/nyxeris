import json
import uuid
import re
import requests
import sqlite3
from pathlib import Path

DB_PATH = Path('data/nyxeris.db')
OLLAMA_URL = 'http://127.0.0.1:11434/api/generate'
MODEL_NAME = 'qwen2.5vl:3b'

CURATED_IMAGES = [
    'https://images.unsplash.com/photo-1544717305-2782549b5136?w=800',
    'https://images.unsplash.com/photo-1593062096033-9a26b09da705?w=800',
    'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800',
    'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800',
    'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=800',
    'https://images.unsplash.com/photo-1616401784845-180882ba9ba8?w=800',
    'https://images.unsplash.com/photo-1558002038-1055907df827?w=800',
    'https://images.unsplash.com/photo-1563770660941-20978e870e26?w=800',
    'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800',
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800',
    'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800',
    'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800'
]

PRODUCT_CONCEPTS = [
    {
        'concept': 'Titanium Heavy Magnetic Cable Management Anchor Dock',
        'category': 'Workspace & Studio',
        'target_price': 45.00,
        'badge': 'New Release',
        'img_idx': 5
    },
    {
        'concept': 'CNC Anodized Aluminum Ergonomic Keyboard Wrist Rest',
        'category': 'Peripherals & Tech',
        'target_price': 59.00,
        'badge': 'Signature',
        'img_idx': 1
    },
    {
        'concept': 'Solid American Walnut and Billet Brass Studio Headphone Stand',
        'category': 'Workspace & Studio',
        'target_price': 79.00,
        'badge': 'Artisan',
        'img_idx': 3
    },
    {
        'concept': 'Apex Magnetic Analog Macropad with Rotary Encoder Knob',
        'category': 'Peripherals & Tech',
        'target_price': 89.00,
        'badge': 'Hall Effect',
        'img_idx': 4
    },
    {
        'concept': 'Volt-100 4-Port GaN Desktop Fast Charging Hub',
        'category': 'Smart Gear & Power',
        'target_price': 85.00,
        'badge': '100W GaN',
        'img_idx': 6
    },
    {
        'concept': 'Monolithic Billet Aluminum Tablet and iPad Pro Stand',
        'category': 'Workspace & Studio',
        'target_price': 69.00,
        'badge': 'Ergonomic',
        'img_idx': 2
    },
    {
        'concept': 'Aero-Grade Carbon Fiber Pocket Scalpel and EDC Utility Blade',
        'category': 'Accessories & EDC',
        'target_price': 48.00,
        'badge': 'Carbon Fiber',
        'img_idx': 7
    },
    {
        'concept': 'Minimalist Precision CNC Titanium Rollerball Pen',
        'category': 'Accessories & EDC',
        'target_price': 65.00,
        'badge': 'Grade 5 Ti',
        'img_idx': 0
    },
    {
        'concept': 'Handcrafted Full-Grain Leather EDC Tech Folio Organizer',
        'category': 'Accessories & EDC',
        'target_price': 110.00,
        'badge': 'Full-Grain',
        'img_idx': 8
    },
    {
        'concept': 'Titanium Quick-Release Shackle Carabiner Keychain',
        'category': 'Accessories & EDC',
        'target_price': 38.00,
        'badge': 'Titanium',
        'img_idx': 9
    },
    {
        'concept': 'Matte Obsidian Acoustic Desk Divider and Tool Organizer',
        'category': 'Workspace & Studio',
        'target_price': 95.00,
        'badge': 'Acoustic Grade',
       'img_idx': 11
    },
    {
        'concept': 'Linear Magnetic Desk Switch Fidget and Keycap Tester Block',
        'category': 'Peripherals & Tech',
        'target_price': 34.00,
        'badge': 'Limited Batch',
       'img_idx': 10
    }
]

def generate_product_with_model(concept_info):
    c_name = concept_info['concept']
    c_cat = concept_info['category']
    prompt = f"Create product copy for luxury piece: {c_name} in category '{c_cat}'. Return a single JSON object with keys: title, description, specs (Material, Finish, Guarantee), variants (2 color names). Return ONLY valid JSON."

    try:
        resp = requests.post(OLLAMA_URL, json={
            'model': MODEL_NAME,
            'prompt': prompt,
            'stream': False
        }, timeout=25)
        raw = resp.json().get('response', '').strip()
        if '{' in raw:
            match = re.search(r'\{.*|}', raw, re.DOTALL)
            if match:
                raw = match.group(0)
        data = json.loads(raw)
        return data
    except Exception as e:
        print(f'Fallback for {concept_info["concept"]}: {e}')
        return {
            'title': concept_info['concept'],
            'description': f'Precision-machined from premium materials, the {concept_info["concept"]} brings understated luxury and tactile satisfaction to any desk setup.',
            'specs': {
                'Material': 'Aerospace Grade Alloy',
                'Finish': 'Matte Anodized Obsidian',
                'Guarantee': '30-Day Transit & Quality Guarantee'
            },
            'variants': [
                {'name': 'Stealth Charcoal', 'in_stock': True},
                {'name': 'Matte Frost', 'in_stock': True}
            ]
        }

def expand_catalog():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    added_count = 0
    for idx, item in enumerate(PRODUCT_CONCEPTS, 1):
        print(f'[{idx}/{len(PRODUCT_CONCEPTS)}] Curating {item["concept"]} via {MODEL_NAME}...')
        ai_data = generate_product_with_model(item)

        prod_id = f'prod_local_{uuid.uuid4().hex[:8]}'
        title = ai_data.get('title', item['concept'])
        clean_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        slug = f"{clean_slug}-{prod_id[-4:]}"
        category = item['category']
        price = float(item['target_price'])
        compare_at = round(price * 1.35, 2)
        cost_price = round(price * 0.35, 2)
        stock = 45 + (idx * 5)
        sku = f"NYX-{category[:3].upper()}-{uuid.uuid4().hex[:4].upper()}"
        image_url = CURATED_IMAGES[item['img_idx']]
        badge = item['badge']
        specs_json = json.dumps(ai_data.get('specs', {}))
        variants_json = json.dumps(ai_data.get('variants', []))

        cursor.execute("""
            INSERT INTO products (
                id, title, slug, description, category, price, compare_at_price,
                cost_price, stock_quantity, sku, supplier_url, image_url, badge,
                specs, variants
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prod_id, title, slug, ai_data.get('description', ''), category,
            price, compare_at, cost_price, stock, sku,
            'https://supplier.nyxeris.internal/' + slug,
            image_url, badge, specs_json, variants_json
        ))

        cursor.execute("""
            INSERT INTO product_reviews (
                product_id, customer_name, rating, title, comment, is_verified_buyer
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            prod_id,
            f"Verified Collector #{idx + 104}",
            5,
            "Flawless machining and fit",
            f"Integrates seamlessly into my workstation. The {title} has a dense, substantial hand-feel with zero sharp edges.",
            1
        ))

        added_count += 1

    conn.commit()
    conn.close()
    print(f"Successfully added {added_count} brand-new luxury products with reviews to {DB_PATH}!")

if __name__ == '__main__':
    expand_catalog()
