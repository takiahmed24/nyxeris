import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def check_checkout_links():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        url = "https://whop.com/dashboard/biz_ea3gy6pg50A7px/links/checkout/"
        print(f"Opening Checkout Links: {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3500)
        page.screenshot(path="data/screenshots/whop_checkout_links.png")
        print("Page Title:", page.title())

        # Inspect table rows and links
        links_data = page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll('tr, div[class*="row"], div[class*="item"]'));
            const anchors = Array.from(document.querySelectorAll('a')).map(a => ({text: a.innerText.trim().replace(/\\n/g, ' '), href: a.href}));
            return {
                anchors: anchors.filter(a => a.href.includes('whop.com') && !a.href.includes('/dashboard/')),
                allText: document.body.innerText.slice(0, 1000).replace(/\\n+/g, ' | ')
            };
        }""")
        print("Checkout links found:")
        import pprint
        pprint.pprint(links_data["anchors"][:10])
        print("\nPage text snippet:\n", links_data["allText"][:400])

        page.close()
        b.close()

if __name__ == "__main__":
    check_checkout_links()
