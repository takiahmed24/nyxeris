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

from config import settings, STATIC_DIR, TEMPLATES_DIR
from database import init_db, get_db_connection
from routes.store_routes import router as store_router
from routes.webhook_routes import router as webhook_router
from routes.admin_routes import router as admin_router

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


@app.on_event("startup")
def on_startup():
    """Ensure database tables and initial catalog are seeded."""
    init_db()


@app.get("/", response_class=HTMLResponse)
async def storefront_page(request: Request):
    """Renders the official Nyxeris Pipeline storefront."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "store_name": settings.STORE_NAME,
        "tagline": settings.STORE_TAGLINE,
        "currency_symbol": settings.STORE_CURRENCY_SYMBOL,
        "free_shipping_threshold": settings.FREE_SHIPPING_THRESHOLD
    })


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
    return templates.TemplateResponse("index.html", {
        "request": request,
        "store_name": settings.STORE_NAME,
        "tagline": settings.STORE_TAGLINE,
        "currency_symbol": settings.STORE_CURRENCY_SYMBOL,
        "free_shipping_threshold": settings.FREE_SHIPPING_THRESHOLD
    })


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

    return templates.TemplateResponse("order_confirmation.html", {
        "request": request,
        "order": order,
        "items": items,
        "store_name": settings.STORE_NAME,
        "support_email": settings.STORE_SUPPORT_EMAIL
    })


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

    return templates.TemplateResponse("payment_gateway.html", {
        "request": request,
        "order": order,
        "items": items,
        "store_name": settings.STORE_NAME
    })


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Renders the Nyxeris Store Owner Cockpit for physical order fulfillment,
    tracking number dispatch, and Whop white-labeling management.
    """
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "store_name": settings.STORE_NAME
    })


@app.get("/themes", response_class=HTMLResponse)
async def themes_showcase_page(request: Request):
    """Renders the interactive Glassmorphic Shopify Theme Showcase & Selector."""
    catalog_file = Path("C:/Nyxeris/data/shopify_themes_catalog.json")
    themes = []
    if catalog_file.exists():
        with open(catalog_file, "r", encoding="utf-8") as f:
            themes = json.load(f)
            
    # Load selected theme if exists
    selected_theme = "Motion"
    sel_file = Path("C:/Nyxeris/data/selected_theme.json")
    if sel_file.exists():
        try:
            with open(sel_file, "r", encoding="utf-8") as f:
                selected_theme = json.load(f).get("selected_theme", "Motion")
        except Exception:
            pass

    return templates.TemplateResponse("theme_showcase.html", {
        "request": request,
        "themes": themes,
        "selected_theme": selected_theme,
        "store_name": settings.STORE_NAME
    })


@app.post("/api/themes/select")
async def select_theme(payload: dict):
    """Selects an active theme for Nyxeris."""
    theme_name = payload.get("theme_name", "Motion")
    data_dir = Path("C:/Nyxeris/data")
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
