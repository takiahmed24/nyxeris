import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
import json
import csv
from pathlib import Path
import config

conn = sqlite3.connect(config.settings.DATABASE_PATH)
c = conn.cursor()
c.execute('SELECT id, title, slug, description, price, compare_at_price, cost_price, stock_quantity, sku, image_url FROM products ORDER BY id')
raw_products = c.fetchall()

def get_accurate_category(pid, title):
    t = title.lower()
    
    overrides = {
        'prod_lumina_pad': 'Workspace & Desk Accessories',
        'prod_obsidian_board': 'Keyboards & Peripherals',
        'prod_apex_audio': 'Audio & Headphones',
        'prod_horizon_light': 'Lighting & Ambience',
        'prod_pulse_dock': 'Smart Gear & Power',
        'prod_edc_tool': 'Precision Tools & EDC',
        'prod_nyxeris_horizon_screenbar_light': 'Lighting & Ambience',
        'prod_nyxeris_matrix_magsafe_station': 'Smart Gear & Power',
        'prod_nyxeris_vektor_titanium_tool': 'Precision Tools & EDC',
        'prod_cj_0001': 'Automotive & Travel',
        'prod_cj_0002': 'Automotive & Travel',
        'prod_cj_0003': 'Workspace & Desk Accessories',
        'prod_cj_0005': 'Automotive & Travel',
        'prod_cj_0006': 'Lighting & Ambience',
        'prod_cj_0007': 'Lighting & Ambience',
        'prod_cj_0008': 'Lighting & Ambience',
        'prod_cj_0009': 'Lighting & Ambience',
        'prod_cj_0010': 'Lighting & Ambience',
        'prod_cj_0011': 'Lighting & Ambience',
        'prod_cj_0012': 'Lighting & Ambience',
        'prod_cj_0013': 'Home, Wellness & Lifestyle',
        'prod_cj_0014': 'Workspace & Desk Accessories',
        'prod_cj_0015': 'Lighting & Ambience',
        'prod_cj_0016': 'Automotive & Travel',
        'prod_cj_0017': 'Automotive & Travel',
        'prod_cj_0018': 'Automotive & Travel',
        'prod_cj_0032': 'Apparel & Outerwear',
        'prod_cj_0040': 'Automotive & Travel',
        'prod_cj_0085': 'Watches & Timepieces',
        'prod_cj_0092': 'Workspace & Desk Accessories',
        'prod_cj_0094': 'Workspace & Desk Accessories',
        'prod_cj_0095': 'Keyboards & Peripherals',
        'prod_cj_0098': 'Keyboards & Peripherals',
        'prod_cj_0110': 'Workspace & Desk Accessories',
        'prod_cj_0111': 'Home, Wellness & Lifestyle',
        'prod_cj_0112': 'Precision Tools & EDC',
        'prod_cj_0113': 'Keyboards & Peripherals',
        'prod_cj_0114': 'Workspace & Desk Accessories',
        'prod_cj_0115': 'Workspace & Desk Accessories',
        'prod_cj_0120': 'Automotive & Travel',
        'prod_cj_0130': 'Automotive & Travel',
        'prod_cj_0135': 'Automotive & Travel',
        'prod_cj_0145': 'Precision Tools & EDC',
        'prod_cj_0154': 'Precision Tools & EDC',
        'prod_cj_0180': 'Automotive & Travel',
        'prod_cj_0181': 'Home, Wellness & Lifestyle',
        'prod_cj_0182': 'Apparel & Outerwear',
        'prod_cj_0183': 'Home, Wellness & Lifestyle',
        'prod_cj_0184': 'Home, Wellness & Lifestyle',
        'prod_cj_0185': 'Automotive & Travel',
        'prod_cj_0187': 'Automotive & Travel',
        'prod_cj_0188': 'Workspace & Desk Accessories',
        'prod_cj_0189': 'Lighting & Ambience',
        'prod_cj_0192': 'Automotive & Travel',
        'prod_cj_0194': 'Workspace & Desk Accessories',
        'prod_cj_0196': 'Home, Wellness & Lifestyle',
    }
    
    if pid in overrides:
        return overrides[pid]
        
    if any(w in t for w in ['watch', 'tourbillon']):
        return 'Watches & Timepieces'
        
    if any(w in t for w in ['jacket', 'coat', 'clothing', 'pants', 'shorts', 'overalls', 'sweater', 'dress', 'leather workwear', 'cowhide']):
        return 'Apparel & Outerwear'
        
    if any(w in t for w in ['keyboard', 'keycap', 'machinery keyboard', 'mouse']):
        return 'Keyboards & Peripherals'
        
    if any(w in t for w in ['headphone', 'earphone', 'headset', 'earbuds', 'dac', 'tune120tws']):
        return 'Audio & Headphones'
        
    if any(w in t for w in ['charger', 'charging', 'power bank', 'magsafe', 'cable', 'data cable', 'type-c', 'usb', 'lithium']):
        return 'Smart Gear & Power'
        
    if any(w in t for w in ['light', 'lamp', 'ambient', 'night light', 'lighting', 'lantern', 'candle', 'linear light']):
        return 'Lighting & Ambience'
        
    if any(w in t for w in ['screwdriver', 'tool set', 'tool box', 'multi-tool', 'knife', 'pen', 'planer', 'drill', 'trimming knife', 'cleaning knife']):
        return 'Precision Tools & EDC'
        
    if any(w in t for w in ['mouse pad', 'desk mat', 'table pad', 'laptop stand', 'monitor', 'holder', 'mount', 'standing desk']):
        return 'Workspace & Desk Accessories'
        
    if any(w in t for w in ['car', 'hud', 'dvr', 'dash cam', 'reversing', 'speed', 'radar', 'navigation']):
        return 'Automotive & Travel'
        
    return 'Home, Wellness & Lifestyle'

updated_count = 0
export_list = []
mapping_template = {}

for pid, title, slug, desc, price, compare_at, cost, stock, sku, image_url in raw_products:
    category = get_accurate_category(pid, title)
    c.execute('UPDATE products SET category = ? WHERE id = ?', (category, pid))
    updated_count += 1
    
    item_dict = {
        'id': pid,
        'title': title,
        'category': category,
        'price': round(float(price), 2),
        'compare_at_price': round(float(compare_at or (price * 1.35)), 2),
        'sku': sku,
        'stock_quantity': stock or 85,
        'image_url': image_url,
        'description': desc
    }
    export_list.append(item_dict)
    mapping_template[pid] = {
        'title': title,
        'category': category,
        'price': round(float(price), 2),
        'sku': sku,
        'whop_product_id': '',
        'whop_checkout_url': ''
    }

conn.commit()
conn.close()

print(f'Successfully updated {updated_count} products in database with accurate categories!')

# Update data/cj_200_products.json if exists
cj_file = Path('data/cj_200_products.json')
if cj_file.exists():
    cj_data = json.load(open(cj_file, 'r', encoding='utf-8'))
    for item in cj_data:
        item['category'] = get_accurate_category(item['id'], item['title'])
    with open(cj_file, 'w', encoding='utf-8') as f:
        json.dump(cj_data, f, indent=2)
    print('Updated data/cj_200_products.json')

# Write whop_products_export.json
with open('data/whop_products_export.json', 'w', encoding='utf-8') as f:
    json.dump(export_list, f, indent=2)
print('Generated data/whop_products_export.json')

# Write whop_products_export.csv
with open('data/whop_products_export.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Internal_Product_ID', 'Product_Name', 'Category', 'Price_USD', 'Compare_Price_USD', 'SKU', 'Stock_Quantity', 'Image_URL', 'Description'])
    for p in export_list:
        writer.writerow([p['id'], p['title'], p['category'], f"{p['price']:.2f}", f"{p['compare_at_price']:.2f}", p['sku'], p['stock_quantity'], p['image_url'], p['description']])
print('Generated data/whop_products_export.csv')

# Write whop_mapping_template.json
with open('data/whop_mapping_template.json', 'w', encoding='utf-8') as f:
    json.dump(mapping_template, f, indent=2)
print('Generated data/whop_mapping_template.json')
