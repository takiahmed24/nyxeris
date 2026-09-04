import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def test_search():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        page = None
        for pg in browser.contexts[0].pages:
            if "cjdropshipping.com" in pg.url:
                page = pg
                break
        
        if not page:
            print("[!] No CJ tab found.")
            return

        print(f"Current page URL: {page.url}")
        page.evaluate("window.scrollBy(0, 350)")
        page.wait_for_timeout(1500)
        page.screenshot(path="data/screenshots/scrolled_cards.png")
        
        cards = page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a[class*="productCard"]'));
            return anchors.map(a => {
                const img = a.querySelector('img');
                const titleEl = a.querySelector('[class*="name"]');
                const priceEl = a.querySelector('[class*="price"]');
                return {
                    href: a.href,
                    title: titleEl ? titleEl.innerText.trim() : a.innerText.trim().slice(0, 80),
                    price: priceEl ? priceEl.innerText.trim() : '',
                    img: img ? (img.src || img.getAttribute('data-src') || '') : ''
                };
            });
        }""")
        print(f"Extracted {len(cards)} live products:")
        import pprint
        pprint.pprint(cards[:10])
        browser.close()

if __name__ == "__main__":
    test_search()
