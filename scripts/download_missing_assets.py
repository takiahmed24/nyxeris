"""Comprehensive Asset Collector & Completeness Engine for Next EUV.

Scans all saved HTML files in c:\\Nyxeris\\nexteuv:
- All stylesheets (<link rel="stylesheet">)
- All scripts (<script src="...">)
- All images (<img src="...">, srcset, data-src)
- All media (<source>, <video>, <audio>)
- All CSS embedded assets (fonts, background images, icons, cursors)
- All Elementor JSON data-settings background images
Downloads any missing assets concurrently into c:\\Nyxeris\\nexteuv.
"""

import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SITE_DIR = Path(r"c:\Nyxeris\nexteuv")
BASE_URL = "https://nexteuv.wpenginepowered.com"
DOMAIN = "nexteuv.wpenginepowered.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(pool_connections=35, pool_maxsize=35, max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Referer": "https://nexteuv.wpenginepowered.com/",
})

def normalize_asset_url(raw_url: str, base: str = BASE_URL) -> str:
    """Normalize raw URL into an absolute remote URL and local relative file path."""
    raw_url = raw_url.strip().strip("'\"")
    if not raw_url or raw_url.startswith("data:") or raw_url.startswith("#") or raw_url.startswith("javascript:"):
        return None
    if raw_url.startswith("//"):
        return "https:" + raw_url
    if raw_url.startswith("/"):
        return BASE_URL + raw_url
    if not urllib.parse.urlparse(raw_url).netloc:
        return urllib.parse.urljoin(base, raw_url)
    return raw_url

def url_to_local_file(url: str) -> Path:
    """Map remote URL to local file path in SITE_DIR."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    if path.startswith("/"):
        path = path[1:]
    path = urllib.parse.unquote(path.split("?")[0].split("#")[0])
    return SITE_DIR / Path(path.replace("/", os.sep))

def download_one(url: str) -> tuple:
    dest = url_to_local_file(url)
    if dest.exists() and dest.stat().st_size > 0:
        return url, dest, True, "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(5):
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 0:
                dest.write_bytes(r.content)
                return url, dest, True, "downloaded"
            elif r.status_code == 429:
                # Rate limited: back off and retry
                time.sleep(2.0 * (attempt + 1))
                continue
            elif r.status_code == 404:
                return url, dest, False, "404"
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return url, dest, False, "failed"

def collect_all_assets() -> set:
    assets = set()
    html_files = list(SITE_DIR.rglob("*.html"))
    print(f"[*] Scanning {len(html_files)} HTML files for asset references...")

    for hf in html_files:
        content = hf.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(content, "html.parser")

        # 1. Stylesheets
        for l in soup.find_all("link", href=True):
            rel = l.get("rel", [])
            if any(r in rel for r in ["stylesheet", "icon", "shortcut icon", "apple-touch-icon", "preload"]):
                norm = normalize_asset_url(l["href"])
                if norm and DOMAIN in norm:
                    assets.add(norm)

        # 2. Scripts
        for s in soup.find_all("script", src=True):
            norm = normalize_asset_url(s["src"])
            if norm and DOMAIN in norm:
                assets.add(norm)

        # 3. Images and Picture sources
        for img in soup.find_all("img"):
            for attr in ["src", "data-src", "data-lazy-src"]:
                val = img.get(attr)
                if val:
                    norm = normalize_asset_url(val)
                    if norm and DOMAIN in norm:
                        assets.add(norm)
            for attr in ["srcset", "data-srcset"]:
                val = img.get(attr)
                if val:
                    for part in val.split(","):
                        u = part.strip().split(" ")[0]
                        norm = normalize_asset_url(u)
                        if norm and DOMAIN in norm:
                            assets.add(norm)

        for source in soup.find_all("source"):
            if source.get("src"):
                norm = normalize_asset_url(source["src"])
                if norm and DOMAIN in norm:
                    assets.add(norm)
            if source.get("srcset"):
                for part in source["srcset"].split(","):
                    u = part.strip().split(" ")[0]
                    norm = normalize_asset_url(u)
                    if norm and DOMAIN in norm:
                        assets.add(norm)

        # 4. Elementor JSON data-settings background images
        for tag in soup.find_all(attrs={"data-settings": True}):
            ds = tag["data-settings"]
            for img_url in re.findall(r'https?:\\/\\/[^"\'\\]+', ds):
                clean_u = img_url.replace("\\/", "/")
                norm = normalize_asset_url(clean_u)
                if norm and DOMAIN in norm:
                    assets.add(norm)

        # 5. Inline CSS url(...)
        for url_match in re.findall(r'url\([\'"]?([^\'")]+)[\'"]?\)', content):
            norm = normalize_asset_url(url_match)
            if norm and DOMAIN in norm:
                assets.add(norm)

    print(f"[*] Discovered {len(assets)} unique HTML-level assets.")
    return assets

def collect_css_nested_assets() -> set:
    css_files = list(SITE_DIR.rglob("*.css"))
    print(f"[*] Scanning {len(css_files)} local CSS files for nested fonts, icons, and background images...")
    nested = set()
    for cf in css_files:
        try:
            content = cf.read_text(encoding="utf-8", errors="ignore")
            # compute base remote URL for this css file
            rel = cf.relative_to(SITE_DIR).as_posix()
            base_remote = f"{BASE_URL}/{rel}"
            for raw_u in re.findall(r'url\([\'"]?([^\'")]+)[\'"]?\)', content):
                raw_u = raw_u.strip()
                if not raw_u or raw_u.startswith("data:") or raw_u.startswith("#"):
                    continue
                norm = normalize_asset_url(raw_u, base=base_remote)
                if norm and DOMAIN in norm:
                    nested.add(norm)
        except Exception:
            pass
    print(f"[*] Discovered {len(nested)} nested assets inside CSS files.")
    return nested

def main():
    print("=================================================================")
    print("           NEXT EUV COMPREHENSIVE ASSET SYNC ENGINE             ")
    print("=================================================================")

    all_assets = collect_all_assets()

    # Determine which are missing
    missing_assets = [u for u in all_assets if not url_to_local_file(u).exists()]
    print(f"[*] Assets status: {len(all_assets) - len(missing_assets)} present, {len(missing_assets)} missing.")

    if missing_assets:
        print(f"[*] Downloading {len(missing_assets)} missing assets in parallel (5 workers with rate-limit backoff)...")
        downloaded = 0
        failed = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(download_one, u): u for u in missing_assets}
            for future in as_completed(futures):
                u, dest, ok, status = future.result()
                if ok:
                    downloaded += 1
                else:
                    failed += 1
                total_done = downloaded + failed
                if total_done % 25 == 0 or total_done == len(missing_assets):
                    print(f"  -> Progress: {total_done}/{len(missing_assets)} (Success: {downloaded}, Fail: {failed})")

    # Now scan downloaded CSS files for nested assets (fonts, icons, etc.)
    nested_assets = collect_css_nested_assets()
    missing_nested = [u for u in nested_assets if not url_to_local_file(u).exists()]
    print(f"[*] Nested CSS assets: {len(nested_assets) - len(missing_nested)} present, {len(missing_nested)} missing.")

    if missing_nested:
        print(f"[*] Downloading {len(missing_nested)} missing nested assets (5 workers)...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(download_one, u): u for u in missing_nested}
            for future in as_completed(futures):
                future.result()

    # Final summary check
    all_final = collect_all_assets()
    still_missing = [u for u in all_final if not url_to_local_file(u).exists()]
    print("\n=================================================================")
    print(f" ASSET SYNC COMPLETE: {len(all_final) - len(still_missing)} / {len(all_final)} assets present locally!")
    if still_missing:
        print(f" [!] {len(still_missing)} remaining missing (likely 404 on live server):")
        for m in still_missing[:10]:
            print(f"     {m}")
    print("=================================================================")

if __name__ == "__main__":
    main()
