"""Main FastAPI application entry point for Nyxeris.
Physical products & dropshipping storefront with white-labeled Whop payment integration.
"""

from pathlib import Path
import json
import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from config import settings, STATIC_DIR, TEMPLATES_DIR, DATA_DIR
from database import init_db, get_db_connection
from routes.store_routes import router as store_router
from routes.webhook_routes import router as webhook_router
from routes.admin_routes import router as admin_router
from routes.auth_routes import router as auth_router

app = FastAPI(
    title="Nyxeris Storefront & Payment Engine",
    description="Physical products and dropshipping platform with white-labeled Whop checkout and receipt delivery.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount Necyron local offline site
NECYRON_DIR = Path(__file__).resolve().parent / "necyron"
if NECYRON_DIR.exists():
    app.mount("/necyron", StaticFiles(directory=str(NECYRON_DIR), html=True), name="necyron")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API Routers
app.include_router(store_router)
app.include_router(webhook_router)
app.include_router(admin_router)
app.include_router(auth_router)


@app.on_event("startup")
def on_startup():
    """Ensure database tables and initial catalog are seeded."""
    init_db()


@app.get("/", response_class=HTMLResponse)
async def storefront_page(request: Request):
    """Renders the official Nyxeris Pipeline storefront."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "store_name": settings.STORE_NAME,
            "tagline": settings.STORE_TAGLINE,
            "currency_symbol": settings.STORE_CURRENCY_SYMBOL,
            "free_shipping_threshold": settings.FREE_SHIPPING_THRESHOLD
        }
    )


@app.get("/home-05", response_class=HTMLResponse)
async def home_05_page(request: Request):
    """Direct route for Onsus Home 05."""
    h5_file = TEMPLATES_DIR / "onsus_home05.html"
    return HTMLResponse(content=h5_file.read_text(encoding="utf-8"))


@app.get("/home-01", response_class=HTMLResponse)
async def home_01_page(request: Request):
    """Direct route for Onsus Home 01."""
    h1_file = TEMPLATES_DIR / "onsus_home01.html"
    return HTMLResponse(content=h1_file.read_text(encoding="utf-8"))


@app.get("/nyxeris", response_class=HTMLResponse)
async def nyxeris_original_storefront(request: Request):
    """Renders the original Nyxeris Hardware storefront."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "store_name": settings.STORE_NAME,
            "tagline": settings.STORE_TAGLINE,
            "currency_symbol": settings.STORE_CURRENCY_SYMBOL,
            "free_shipping_threshold": settings.FREE_SHIPPING_THRESHOLD
        }
    )


@app.api_route("/api/wc-ajax", methods=["GET", "POST"])
async def local_wc_ajax():
    """Local offline mock handler for WooCommerce AJAX requests."""
    return {
        "result": "success",
        "fragments": {
            "div.widget_shopping_cart_content": "<div class='widget_shopping_cart_content'><p class='woocommerce-mini-cart__empty-message'>No products in the cart.</p></div>"
        },
        "cart_hash": "local_mock_hash"
    }


@app.api_route("/api/tf-ajax", methods=["GET", "POST"])
async def local_tf_ajax():
    """Local offline mock handler for Themesflat AJAX requests."""
    return {"status": "success", "message": "Action recorded locally"}


@app.get("/policies/refunds", response_class=HTMLResponse)
async def policy_refunds_page(request: Request):
    """Renders the official Nyxeris 30-Day Transit & Quality Guarantee."""
    html_content = """
    <h2>1. 30-Day Unconditional Quality Guarantee</h2>
    <p>Every piece engineered and dispatched by Nyxeris is backed by our strict 30-day satisfaction commitment. If you are not entirely satisfied with the craftsmanship, material density, or ergonomic performance of your gear, you may initiate a return or exchange within 30 calendar days of confirmed carrier delivery.</p>
    
    <div class="guarantee-grid">
      <div class="guarantee-item">
        <div class="guarantee-item-title">Zero Hassle Returns</div>
        <p class="guarantee-item-desc">30 days from delivery date to inspect, test, and verify fit in your setup.</p>
      </div>
      <div class="guarantee-item">
        <div class="guarantee-item-title">Immediate Replacement</div>
        <p class="guarantee-item-desc">Transit damage or defect? We ship an express replacement before return pickup.</p>
      </div>
      <div class="guarantee-item">
        <div class="guarantee-item-title">3-5 Day Payouts</div>
        <p class="guarantee-item-desc">Refunds routed directly to your original payment card via Whop Secure Gateway.</p>
      </div>
    </div>

    <h2>2. Damaged or Lost in Transit Protection</h2>
    <p>All Nyxeris shipments travel under fully insured carrier manifests. In the unlikely event that your parcel sustains damage during air courier transit or fails to show carrier movement past 15 business days, our Concierge team immediately dispatches a brand-new unit at no additional cost or issues a 100% full refund.</p>

    <div class="highlight-box">
      <p><strong>To report an issue:</strong> Contact <strong>concierge@nyxeris.com</strong> or your Account Order Portal with your 12-digit Nyxeris Order ID (e.g. <code>NYX-1A2B3C4D5E6F</code>) and our dispatch team will resolve your request within 12 hours.</p>
    </div>

    <h2>3. Return Eligibility Requirements</h2>
    <ul>
      <li>Item must remain in pristine functional condition with original serialized parts.</li>
      <li>Packaging should include original inner protective sleeves and bundled accessories.</li>
      <li>Custom bespoke engraved pieces are subject to a standard re-polishing deduction unless defective.</li>
    </ul>

    <h2>4. Refund Processing Window</h2>
    <p>Once your returned item arrives at our inspection depot, your refund is credited within 3-5 business days. Your banking institution will reflect the credit according to standard processing times.</p>
    """
    return templates.TemplateResponse(
        request=request,
        name="policy_page.html",
        context={
            "policy_title": "30-Day Transit & Quality Guarantee",
            "policy_badge": "Guaranteed Satisfaction",
            "active_policy": "refunds",
            "policy_html": html_content
        }
    )


@app.get("/policies/shipping", response_class=HTMLResponse)
async def policy_shipping_page(request: Request):
    """Renders the official Nyxeris Priority Shipping & Delivery Policy."""
    html_content = """
    <h2>1. Dispatch & Courier Networks</h2>
    <p>Nyxeris partners exclusively with tier-one express logistics networks (USPS Priority, DHL Express, FedEx Air, and Royal Mail) to ensure that your precision workspace hardware reaches your desk quickly and unharmed.</p>

    <div class="guarantee-grid">
      <div class="guarantee-item">
        <div class="guarantee-item-title">Continental United States</div>
        <p class="guarantee-item-desc"><strong>$14.99</strong> Flat Priority Courier (Free on orders $120+). 4 to 8 business days.</p>
      </div>
      <div class="guarantee-item">
        <div class="guarantee-item-title">United Kingdom & Europe</div>
        <p class="guarantee-item-desc"><strong>$16.99</strong> Tracked Air Courier (VAT prepaid). 6 to 10 business days.</p>
      </div>
      <div class="guarantee-item">
        <div class="guarantee-item-title">Rest of World</div>
        <p class="guarantee-item-desc"><strong>$19.99</strong> Worldwide Insured Express. 7 to 12 business days.</p>
      </div>
    </div>

    <h2>2. Processing & Fulfillment Timelines</h2>
    <p>All in-stock orders are processed, quality-inspected, and dispatched within 24 to 48 business hours. As soon as your shipment leaves our facility, you will receive an automated dispatch notification with your real-time tracking number and carrier link.</p>

    <h2>3. Premium Bespoke Unboxing ($2.99)</h2>
    <p>Customers may opt for the <strong>Nyxeris Signature Protective Box</strong> at checkout. This includes dual-density high-rebound foam cushioning, water-repellent matte obsidian sleeve, and an individualized metallic authenticity certificate card.</p>

    <h2>4. Customs, Duties & Tariffs</h2>
    <p>For US, UK, and EU orders, customs and duties are handled and cleared prior to doorstep arrival. For destinations subject to local import declarations, carrier brokers will contact you directly to facilitate clearance without warehouse delays.</p>
    """
    return templates.TemplateResponse(
        request=request,
        name="policy_page.html",
        context={
            "policy_title": "Shipping & Insured Transit Policy",
            "policy_badge": "Global Logistics",
            "active_policy": "shipping",
            "policy_html": html_content
        }
    )


@app.get("/policies/privacy", response_class=HTMLResponse)
async def policy_privacy_page(request: Request):
    """Renders the official Nyxeris Privacy & Data Protection Policy."""
    html_content = """
    <h2>1. Our Privacy Philosophy</h2>
    <p>Nyxeris operates under a strict privacy-first architecture. We do not sell, rent, or trade your personal information, browsing history, or payment credentials to third-party advertising brokers under any circumstances.</p>

    <h2>2. Data Collection & Use</h2>
    <p>We collect only the minimum information necessary to execute and fulfill your hardware orders:</p>
    <ul>
      <li><strong>Contact Information:</strong> Full name and email address to send digital receipts, order tracking updates, and account credentials.</li>
      <li><strong>Shipping Address:</strong> Street, city, state/province, and postal code required by couriers for physical delivery.</li>
      <li><strong>Session & Security Data:</strong> Cryptographic session tokens and authentication tokens to keep your account secure.</li>
    </ul>

    <h2>3. Payment Security & PCI-DSS Compliance</h2>
    <p>Nyxeris never touches or stores raw credit card numbers or banking secrets on our servers. All financial transactions are tokenized and processed through Whop Payments and Stripe infrastructure, adhering to Level 1 PCI-DSS compliance and AES-256 end-to-end encryption.</p>

    <h2>4. GDPR & CCPA Rights</h2>
    <p>Under global data privacy frameworks (including the European General Data Protection Regulation and California Consumer Privacy Act), you retain full rights to:</p>
    <ul>
      <li>Request an export of all personal data tied to your email account.</li>
      <li>Request permanent erasure of customer profiles and delivery logs.</li>
      <li>Opt-out of product update and engineering journal newsletters at any time.</li>
    </ul>

    <div class="highlight-box">
      <p>To exercise your privacy rights or request data erasure, contact our Data Protection Officer at <strong>privacy@nyxeris.com</strong>.</p>
    </div>
    """
    return templates.TemplateResponse(
        request=request,
        name="policy_page.html",
        context={
            "policy_title": "Privacy & Data Protection Policy",
            "policy_badge": "Privacy-First Architecture",
            "active_policy": "privacy",
            "policy_html": html_content
        }
    )


@app.get("/policies/terms", response_class=HTMLResponse)
async def policy_terms_page(request: Request):
    """Renders the official Nyxeris Terms of Service."""
    html_content = """
    <h2>1. Agreement to Terms</h2>
    <p>By accessing the Nyxeris storefront, creating an account, or placing an order for hardware, you agree to be bound by these Terms of Service and all applicable international trade regulations.</p>

    <h2>2. Orders & Commercial Transactions</h2>
    <p>All orders placed through our digital storefront represent an offer to purchase. Acceptance occurs upon dispatch notification and generation of your official serialized Nyxeris PDF tax receipt. We reserve the right to decline or cancel orders exhibiting anomalous fraud flags or automated bot purchasing activity.</p>

    <h2>3. Product Descriptions & Specifications</h2>
    <p>We endeavor to present dimensions, finishes, anodization coatings, and magnetic switch specifications with laboratory accuracy. Minor tolerances inherent to CNC machining, natural vegan leather grain, or monitor display color gamuts are normal.</p>

    <h2>4. Limitation of Liability</h2>
    <p>To the maximum extent permitted by applicable law, Nyxeris and its suppliers shall not be liable for any indirect, incidental, or consequential damages resulting from the use or inability to use our physical hardware.</p>

    <h2>5. Governing Law & Dispute Resolution</h2>
    <p>These terms shall be governed by and construed in accordance with the laws governing commercial electronic trade, without giving effect to conflict of law principles. Any dispute arising under these terms shall be settled via direct concierge mediation before arbitration.</p>
    """
    return templates.TemplateResponse(
        request=request,
        name="policy_page.html",
        context={
            "policy_title": "Terms of Service",
            "policy_badge": "Commercial Agreement",
            "active_policy": "terms",
            "policy_html": html_content
        }
    )


@app.get("/order-confirmation/{order_id}", response_class=HTMLResponse)
async def order_confirmation_page(request: Request, order_id: str):
    """Renders customer order confirmation and tracking with one-click Nyxeris PDF receipt download."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    order_row = cursor.fetchone()

    if not order_row:
        conn.close()
        return HTMLResponse(content="<h3>Order not found.</h3>", status_code=404)

    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    items = [dict(r) for r in cursor.fetchall()]
    order = dict(order_row)
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="order_confirmation.html",
        context={
            "order": order,
            "items": items,
            "store_name": settings.STORE_NAME,
            "support_email": settings.STORE_SUPPORT_EMAIL
        }
    )


@app.get("/checkout/pay/{order_id}", response_class=HTMLResponse)
async def checkout_payment_gateway_page(request: Request, order_id: str):
    """Renders the clean Nyxeris Checkout Gateway interface.
    Allows customers/testers to finalize payments seamlessly with 100% Nyxeris branding.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    order_row = cursor.fetchone()

    if not order_row:
        conn.close()
        return HTMLResponse(content="<h3>Order not found.</h3>", status_code=404)

    order = dict(order_row)
    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    items = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="payment_gateway.html",
        context={
            "order": order,
            "items": items,
            "store_name": settings.STORE_NAME
        }
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Renders the Nyxeris Store Owner Cockpit for physical order fulfillment,
    tracking number dispatch, and Whop white-labeling management.
    """
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "store_name": settings.STORE_NAME
        }
    )


@app.get("/themes", response_class=HTMLResponse)
async def themes_showcase_page(request: Request):
    """Renders the interactive Glassmorphic Shopify Theme Showcase & Selector."""
    catalog_file = DATA_DIR / "shopify_themes_catalog.json"
    themes = []
    if catalog_file.exists():
        with open(catalog_file, "r", encoding="utf-8") as f:
            themes = json.load(f)
            
    # Load selected theme if exists
    selected_theme = "Motion"
    sel_file = DATA_DIR / "selected_theme.json"
    if sel_file.exists():
        try:
            with open(sel_file, "r", encoding="utf-8") as f:
                selected_theme = json.load(f).get("selected_theme", "Motion")
        except Exception:
            pass

    return templates.TemplateResponse(
        request=request,
        name="theme_showcase.html",
        context={
            "themes": themes,
            "selected_theme": selected_theme,
            "store_name": settings.STORE_NAME
        }
    )


@app.post("/api/themes/select")
async def select_theme(payload: dict):
    """Selects an active theme for Nyxeris."""
    theme_name = payload.get("theme_name", "Motion")
    data_dir = DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / "selected_theme.json", "w", encoding="utf-8") as f:
        json.dump({
            "selected_theme": theme_name,
            "updated_at": datetime.datetime.now().isoformat()
        }, f, indent=2)
    return {"status": "success", "selected_theme": theme_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
