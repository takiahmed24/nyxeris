import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def check_edc():
    queries = ["edc multi tool", "multitool pliers"]
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        for q in queries:
            url = f"https://cjdropshipping.com/search/{q.replace(' ', '+')}.html"
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3500)
            cards = page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('a[class*="productCard"]'));
                return anchors.map(a => {
                    const titleEl = a.querySelector('[class*="name"]');
                    const priceEl = a.querySelector('[class*="price"]');
                    const img = a.querySelector('img');
                    return {
                        title: titleEl ? titleEl.innerText.trim() : a.innerText.trim(),
                        price: priceEl ? priceEl.innerText.trim() : '',
                        href: a.href,
                        img: img ? (img.src || img.getAttribute('data-src') || '') : ''
                    };
                }).slice(0, 5);
            }""")
            print(f"\nResults for '{q}':")
            for idx, c in enumerate(cards):
                print(f"  [{idx+1}] {c['title']} | Price: {c['price']}")
                print(f"      Link: {c['href']}")
        page.close()
        b.close()

if __name__ == "__main__":
    check_edc()
