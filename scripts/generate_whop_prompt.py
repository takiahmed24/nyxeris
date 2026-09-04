import json

with open("data/whop_products_export.json", "r", encoding="utf-8") as f:
    products = json.load(f)

prompt_content = """# Instructions for Whop AI

You are acting as the e-commerce store setup assistant for **Nyxeris / Curated Modern Goods**.
Please create the following products in my Whop store. For each product:
- Set the **Product Title** exactly as specified.
- Set the **One-Time Price (USD)** to the specified price.
- Assign the product to the corresponding **Category / Collection**.
- Attach the **Product Image URL**.
- Set the **SKU** in product metadata.

After creating or configuring the products, **YOU MUST RETURN A CLEAN JSON BLOCK** mapping each product's `internal_id` to its created `whop_product_id` and `whop_checkout_url` (or plan link) so that the storefront can immediately be linked:

```json
{
  "prod_lumina_pad": {
    "whop_product_id": "prod_XXXXXXXXXX",
    "whop_checkout_url": "https://whop.com/checkout/plan_XXXXXXXXXX"
  }
}
```

---

## Complete Product Catalog (205 Products)

"""

# Group products by category for clean readability
by_cat = {}
for p in products:
    by_cat.setdefault(p["category"], []).append(p)

for cat_name, cat_items in sorted(by_cat.items()):
    prompt_content += f"### Department: {cat_name} ({len(cat_items)} Products)\n\n"
    prompt_content += "| Internal ID | Product Title | Price (USD) | SKU | Image URL |\n"
    prompt_content += "| :--- | :--- | :--- | :--- | :--- |\n"
    for item in cat_items:
        title_esc = item["title"].replace("|", "-")
        prompt_content += f"| `{item['id']}` | {title_esc} | ${item['price']:.2f} | `{item['sku']}` | [Image]({item['image_url']}) |\n"
    prompt_content += "\n"

with open("data/WHOP_AI_PROMPT.md", "w", encoding="utf-8") as f:
    f.write(prompt_content)

print(f"Generated data/WHOP_AI_PROMPT.md with {len(products)} products across {len(by_cat)} categories!")
