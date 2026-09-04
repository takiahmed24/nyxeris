import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CDP_URL = "http://127.0.0.1:9222"

def inspect_nyxeris_store():
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP_URL)
        page = b.contexts[0].new_page()
        url = "https://whop.com/nyxeris/"
        print(f"Navigating to public Whop store: {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(4000)
        page.screenshot(path="data/screenshots/whop_public_nyxeris_store.png")
        print("Page Title:", page.title())

        # Check product links on the public store
        links = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('a'))
                .map(a => ({href: a.href, text: a.innerText.trim().replace(/\\n/g, ' ')}))
                .filter(x => x.href.includes('whop.com/nyxeris/') || x.href.includes('/checkout/'));
        }""")
        print(f"Public store links found ({len(links)}):")
        import pprint
        pprint.pprint(links[:15])

        page.close()
        b.close()

if __name__ == "__main__":
    inspect_nyxeris_store()
