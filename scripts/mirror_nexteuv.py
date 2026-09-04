"""Complete offline mirror and localization engine for Next EUV (Electric Vehicles Showcase).

Crawls all pages (Home 1, 2, 3, Shop Cars/Drones/Scooters, all products, blogs, About, Contact, etc.),
downloads all stylesheets, scripts, responsive images (srcset), Google Fonts (Lexend Deca, DM Sans),
Elementor webfonts (eicons, fontawesome), deep-scans CSS files for url(...) assets, rewrites links,
and saves the site for 100% offline local browsing.
"""

import os
import re
import sys
import time
import json
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Ensure unbuffered stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

BASE_URL = "https://nexteuv.wpenginepowered.com/"
DOMAIN = "nexteuv.wpenginepowered.com"
OUTPUT_DIR = Path(r"c:\Nyxeris\nexteuv")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# Setup high performance requests session with connection pooling
session = requests.Session()
retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})

SEED_PAGES = [
    "",
    "home-1/",
    "home-2/",
    "home-3/",
    "about/",
    "service/",
    "pricing-plans/",
    "gallery/",
    "faq/",
    "contact/",
    "cart/",
    "404",
    "shop-cars/",
    "shop-drones/",
    "shop-e-scooter/",
    "blog-cars/",
    "blog-drones/",
    "blog-e-scooter/",
]

NON_HTML_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".json", ".mp4",
    ".pdf", ".zip", ".xml", ".txt"
)

def is_valid_page_rel(rel_path: str) -> bool:
    """Determine if a relative path is an HTML page and not an asset or feed."""
    lower = rel_path.lower().strip("/")
    if not lower:
        return True
    if any(lower.endswith(ext) for ext in NON_HTML_EXTENSIONS):
        return False
    if any(seg in lower for seg in ["wp-content", "wp-includes", "wp-json", "feed", "wp-admin", "wp-login"]):
        return False
    return True

def clean_url_path(url: str) -> str:
    """Extract clean URL path without query params or anchors."""
    parsed = urllib.parse.urlparse(url)
    return parsed.path

def url_to_local_path(url: str) -> Path:
    """Map a remote URL to local destination path in OUTPUT_DIR."""
    parsed = urllib.parse.urlparse(url)
    rel_path = parsed.path
    if rel_path.startswith("/"):
        rel_path = rel_path[1:]
    rel_path = rel_path.split("?")[0].split("#")[0]
    rel_path = urllib.parse.unquote(rel_path)
    safe_rel = Path(rel_path.replace("/", os.sep))
    return OUTPUT_DIR / safe_rel

def download_file(url: str, dest: Path) -> bool:
    """Download a file with retry logic using persistent session."""
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)

    if url.startswith("//"):
        url = "https:" + url

    for attempt in range(3):
        try:
            r = session.get(url, timeout=12, stream=True)
            if r.status_code == 200:
                dest.write_bytes(r.content)
                return True
        except Exception:
            time.sleep(0.3 * (attempt + 1))
    return False

def download_and_localize_google_fonts(font_urls: set, output_dir: Path) -> dict:
    """Download Google Font stylesheets and embedded WOFF2 files."""
    google_fonts_dir = output_dir / "assets" / "fonts" / "google"
    google_fonts_dir.mkdir(parents=True, exist_ok=True)

    replacements = {}
    font_count = 0

    for idx, g_url in enumerate(font_urls):
        try:
            full_url = g_url
            if full_url.startswith("//"):
                full_url = "https:" + full_url
            r = session.get(full_url, timeout=12)
            if r.status_code != 200:
                continue
            css_text = r.text

            woff_urls = re.findall(r'url\((https?://fonts\.gstatic\.com/[^)]+)\)', css_text)
            for w_url in woff_urls:
                font_filename = Path(urllib.parse.urlparse(w_url).path).name
                local_font_file = google_fonts_dir / font_filename
                download_file(w_url, local_font_file)
                css_text = css_text.replace(w_url, f"/assets/fonts/google/{font_filename}")
                font_count += 1

            local_css_name = f"google_font_{idx+1}.css"
            local_css_path = google_fonts_dir / local_css_name
            local_css_path.write_text(css_text, encoding="utf-8")
            replacements[g_url] = f"/assets/fonts/google/{local_css_name}"
        except Exception as e:
            print(f"[WARN] Could not localize Google Font {g_url}: {e}")

    print(f"[*] Localized {len(replacements)} Google Font stylesheets with {font_count} WOFF2 files.")
    return replacements

def main():
    print("=================================================================")
    print("             NEXT EUV COMPLETE OFFLINE MIRROR ENGINE             ")
    print("=================================================================")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Page discovery and parallel fetching
    print("\n[Step 1/5] Discovering and fetching all site pages...")
    discovered = set()
    to_visit = set([p.strip("/") for p in SEED_PAGES if is_valid_page_rel(p)])
    html_pages = {}

    def fetch_single_page(rel_subpath):
        target = urllib.parse.urljoin(BASE_URL, rel_subpath + ("/" if rel_subpath else ""))
        try:
            r = session.get(target, timeout=12)
            if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
                return rel_subpath, target, r.text
        except Exception as e:
            pass
        return rel_subpath, target, None

    iteration = 0
    max_iterations = 5
    while to_visit and iteration < max_iterations:
        iteration += 1
        current_batch = list(to_visit - discovered)
        if not current_batch:
            break
        print(f" -> Crawl wave {iteration}: Fetching {len(current_batch)} pages in parallel...")
        discovered.update(current_batch)

        new_links = set()
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(fetch_single_page, p): p for p in current_batch}
            for future in as_completed(futures):
                rel_p, full_url, html = future.result()
                if html:
                    html_pages[rel_p] = html
                    soup = BeautifulSoup(html, "html.parser")
                    for a in soup.find_all("a", href=True):
                        raw_href = urllib.parse.urljoin(full_url, a["href"]).split("#")[0].split("?")[0]
                        p = urllib.parse.urlparse(raw_href)
                        if p.netloc == DOMAIN:
                            clean_rel = p.path.strip("/")
                            if is_valid_page_rel(clean_rel) and clean_rel not in discovered:
                                new_links.add(clean_rel)

        to_visit = new_links
        print(f"    Wave {iteration} complete. Total fetched so far: {len(html_pages)} pages.")

    print(f"[*] Successfully retrieved {len(html_pages)} unique pages across the site.")

    # 2. Extract asset references
    print("\n[Step 2/5] Parsing all asset references from HTML...")
    all_asset_urls = set()
    google_font_urls = set()

    for subpath, html in html_pages.items():
        # Google fonts
        for g_link in re.findall(r'href=[\'"]((?:https?:)?//fonts\.googleapis\.com/[^\'"]+)[\'"]', html):
            clean_g = g_link.replace("&amp;", "&").replace("&#038;", "&")
            google_font_urls.add(clean_g)

        # Standard src/href tags
        for match in re.findall(r'(?:href|src)=[\'"]([^\'"]+)[\'"]', html):
            full = urllib.parse.urljoin(BASE_URL, match)
            if DOMAIN in full:
                clean_path = clean_url_path(full)
                if any(clean_path.lower().endswith(ext) for ext in [
                    '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp',
                    '.ico', '.woff', '.woff2', '.ttf', '.eot', '.otf', '.json', '.mp4'
                ]):
                    all_asset_urls.add(full)

        # Srcset images
        for srcset in re.findall(r'srcset=[\'"]([^\'"]+)[\'"]', html):
            parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
            for p in parts:
                full = urllib.parse.urljoin(BASE_URL, p)
                if DOMAIN in full:
                    all_asset_urls.add(full)

        # Background images in inline styles
        for bg in re.findall(r'url\([\'"]?(https?://[^/]*' + re.escape(DOMAIN) + r'/[^\'")]+)[\'"]?\)', html):
            all_asset_urls.add(bg)

    print(f"[*] Discovered {len(all_asset_urls)} direct site assets and {len(google_font_urls)} Google Font links.")

    # 3. Localize Google Fonts
    print("\n[Step 3/5] Localizing Google Fonts...")
    google_replacements = download_and_localize_google_fonts(google_font_urls, OUTPUT_DIR)

    # 4. Download direct assets and deep scan CSS for nested assets
    print(f"\n[Step 4/5] Downloading {len(all_asset_urls)} assets and resolving CSS nested fonts/images...")
    css_files_to_parse = []

    def fetch_asset(u):
        dest = url_to_local_path(u)
        ok = download_file(u, dest)
        return u, dest, ok

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_asset, u): u for u in all_asset_urls}
        completed_count = 0
        for future in as_completed(futures):
            u, dest, ok = future.result()
            completed_count += 1
            if completed_count % 75 == 0 or completed_count == len(all_asset_urls):
                print(f"  -> Direct assets: {completed_count}/{len(all_asset_urls)} completed...")
            if ok and dest.name.endswith(".css"):
                css_files_to_parse.append((u, dest))

    print(f"[*] Scanning {len(css_files_to_parse)} CSS stylesheets for webfonts and background images...")
    nested_assets = set()
    for base_css_url, css_path in css_files_to_parse:
        try:
            content = css_path.read_text(encoding="utf-8", errors="ignore")
            urls = re.findall(r'url\([\'"]?([^()\'"]+)[\'"]?\)', content)
            for raw_u in urls:
                raw_u = raw_u.strip()
                if raw_u.startswith("data:") or raw_u.startswith("#") or not raw_u:
                    continue
                resolved = urllib.parse.urljoin(base_css_url, raw_u)
                if DOMAIN in resolved or not urllib.parse.urlparse(resolved).netloc:
                    nested_assets.add(resolved)
        except Exception:
            pass

    print(f"[*] Found {len(nested_assets)} nested CSS assets (fonts/icons/images). Downloading...")
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_asset, u): u for u in nested_assets}
        nested_completed = 0
        for future in as_completed(futures):
            future.result()
            nested_completed += 1
            if nested_completed % 50 == 0 or nested_completed == len(nested_assets):
                print(f"  -> Nested assets: {nested_completed}/{len(nested_assets)} completed...")

    # 5. Process and write HTML files
    print("\n[Step 5/5] Rewriting internal links, Google font references, and saving HTML pages...")
    saved_count = 0
    for subpath, html in html_pages.items():
        # Replace Google fonts
        for g_url, local_g in google_replacements.items():
            html = html.replace(g_url, local_g)
            html = html.replace(g_url.replace("&", "&#038;"), local_g)
            html = html.replace(g_url.replace("&", "&amp;"), local_g)

        # Replace elementor JSON encoded URLs
        html = html.replace(r"https:\/\/nexteuv.wpenginepowered.com\/", "/")
        html = html.replace(r"https:\/\/nexteuv.wpenginepowered.com", "")
        html = html.replace(r"http:\/\/nexteuv.wpenginepowered.com\/", "/")
        html = html.replace(r"http:\/\/nexteuv.wpenginepowered.com", "")

        # Replace absolute domain URLs with root-relative paths
        html = html.replace("https://nexteuv.wpenginepowered.com/", "/")
        html = html.replace("http://nexteuv.wpenginepowered.com/", "/")
        html = html.replace("//nexteuv.wpenginepowered.com/", "/")
        html = html.replace("https://nexteuv.wpenginepowered.com", "/")
        html = html.replace("http://nexteuv.wpenginepowered.com", "/")

        # Save to appropriate [subpath]/index.html
        if subpath == "":
            dest_html = OUTPUT_DIR / "index.html"
        else:
            dest_html = OUTPUT_DIR / subpath / "index.html"

        dest_html.parent.mkdir(parents=True, exist_ok=True)
        dest_html.write_text(html, encoding="utf-8")
        saved_count += 1

    # Also make a copy of 404/index.html to 404.html at root if present
    four_oh_four = OUTPUT_DIR / "404" / "index.html"
    if four_oh_four.exists():
        (OUTPUT_DIR / "404.html").write_bytes(four_oh_four.read_bytes())

    print("\n=================================================================")
    print(f"   NEXT EUV MIRROR COMPLETE! Total Pages Saved: {saved_count}    ")
    print(f"   Local Output Directory: {OUTPUT_DIR}                         ")
    print("=================================================================")

if __name__ == "__main__":
    main()

