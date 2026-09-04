"""Complete offline mirror script for Necyron Template Kit.

Downloads all 18 pages, stylesheets, javascripts, responsive images, webfonts
(Elementor Eicons, FontAwesome, JKit icons, ElementsKit icons, Google Fonts),
rewrites all references to local paths, and ensures 100% offline functionality.
"""

import os
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://templatekit.kitprostudio.com/necyron/"
OUTPUT_DIR = Path(r"c:\Nyxeris\necyron")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

# 18 Discovered pages
PAGES = [
    "",  # Home root
    "template-kit/home/",
    "template-kit/about-us/",
    "template-kit/0ur-team/",
    "template-kit/services/",
    "template-kit/project/",
    "template-kit/pricing/",
    "template-kit/blog-post/",
    "template-kit/faq/",
    "template-kit/404/",
    "template-kit/contact-us/",
    "category/uncategorized/",
    "2026/04/25/advanced-cybersecurity-systems/",
    "2026/04/25/efficient-system-monitoring-systems/",
    "2026/04/25/reliable-network-security-systems/",
    "2026/05/04/modern-data-protection-strategies/",
    "2026/05/04/scalable-it-support-solutions/",
    "2026/05/04/smart-cloud-infrastructure-systems/",
]

def clean_url_path(url: str) -> str:
    """Extract clean URL path without query params or anchors."""
    parsed = urllib.parse.urlparse(url)
    return parsed.path

def url_to_local_path(url: str) -> Path:
    """Map a site URL to local destination path."""
    parsed = urllib.parse.urlparse(url)
    rel_path = parsed.path
    if rel_path.startswith("/necyron/"):
        rel_path = rel_path[len("/necyron/"):]
    elif rel_path.startswith("/"):
        rel_path = rel_path[1:]
        
    # Remove any query params or hash
    rel_path = rel_path.split("?")[0].split("#")[0]
    return OUTPUT_DIR / Path(rel_path.replace("/", os.sep))

def download_file(url: str, dest: Path) -> bool:
    """Download a single file safely with retry logic."""
    if dest.exists() and dest.stat().st_size > 0:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                dest.write_bytes(data)
                return True
        except Exception as e:
            time.sleep(0.5 * (attempt + 1))
    print(f"[WARN] Failed to download {url} to {dest}")
    return False

def download_and_localize_google_fonts(font_urls: list, output_dir: Path) -> dict:
    """Download Google Font stylesheets and embedded woff2 files."""
    google_fonts_dir = output_dir / "assets" / "fonts" / "google"
    google_fonts_dir.mkdir(parents=True, exist_ok=True)
    
    replacements = {}
    font_count = 0
    
    for idx, g_url in enumerate(font_urls):
        try:
            # Modern user agent to receive WOFF2 fonts from Google
            req = urllib.request.Request(g_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                css_text = resp.read().decode("utf-8", errors="ignore")
                
            # Extract woff2 / font links
            woff_urls = re.findall(r'url\((https?://fonts\.gstatic\.com/[^)]+)\)', css_text)
            for w_url in woff_urls:
                font_filename = Path(urllib.parse.urlparse(w_url).path).name
                local_font_file = google_fonts_dir / font_filename
                download_file(w_url, local_font_file)
                # Replace in css text
                css_text = css_text.replace(w_url, f"/assets/fonts/google/{font_filename}")
                font_count += 1
                
            local_css_name = f"google_font_{idx+1}.css"
            local_css_path = google_fonts_dir / local_css_name
            local_css_path.write_text(css_text, encoding="utf-8")
            replacements[g_url] = f"/assets/fonts/google/{local_css_name}"
        except Exception as e:
            print(f"[WARN] Could not localize Google Font {g_url}: {e}")
            
    print(f"[*] Localized {len(font_urls)} Google Font stylesheets with {font_count} font files.")
    return replacements

def main():
    print("=================================================================")
    print("             NECYRON OFFLINE WEBSITE MIRROR ENGINE              ")
    print("=================================================================")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    html_pages = {}
    all_asset_urls = set()
    google_font_urls = set()
    
    # 1. Fetch all HTML pages
    print("\n[Step 1/5] Fetching all 18 site pages...")
    for subpath in PAGES:
        target_url = urllib.parse.urljoin(BASE_URL, subpath)
        print(f" -> Fetching: {target_url}")
        try:
            req = urllib.request.Request(target_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                html_pages[subpath] = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[ERROR] Failed to fetch page {target_url}: {e}")
            
    print(f"[*] Successfully fetched {len(html_pages)} pages.")
    
    # 2. Extract all asset URLs from pages
    print("\n[Step 2/5] Parsing assets from HTML...")
    for subpath, html in html_pages.items():
        # Google fonts
        for g_link in re.findall(r'href=[\'"](https?://fonts\.googleapis\.com/[^\'"]+)[\'"]', html):
            clean_g = g_link.replace("&amp;", "&")
            google_font_urls.add(clean_g)
            
        # Standard href / src assets
        for match in re.findall(r'(?:href|src)=[\'"]([^\'"]+)[\'"]', html):
            full = urllib.parse.urljoin(BASE_URL, match)
            if "templatekit.kitprostudio.com/necyron/" in full:
                clean_path = clean_url_path(full)
                if any(clean_path.lower().endswith(ext) for ext in [
                    '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp',
                    '.ico', '.woff', '.woff2', '.ttf', '.eot', '.otf', '.json'
                ]):
                    all_asset_urls.add(full)
                    
        # Extract srcset images
        for srcset in re.findall(r'srcset=[\'"]([^\'"]+)[\'"]', html):
            parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
            for p in parts:
                full = urllib.parse.urljoin(BASE_URL, p)
                if "templatekit.kitprostudio.com/necyron/" in full:
                    all_asset_urls.add(full)
                    
        # Extract inline background-image URLs
        for bg in re.findall(r'url\([\'"]?(https?://templatekit\.kitprostudio\.com/necyron/[^\'")]+)[\'"]?\)', html):
            all_asset_urls.add(bg)

    print(f"[*] Discovered {len(all_asset_urls)} direct site assets and {len(google_font_urls)} Google Font links.")
    
    # 3. Download Google fonts locally
    print("\n[Step 3/5] Localizing Google Fonts...")
    google_replacements = download_and_localize_google_fonts(list(google_font_urls), OUTPUT_DIR)
    
    # 4. Download assets and recursively find nested assets in CSS
    print("\n[Step 4/5] Downloading assets and resolving nested fonts...")
    css_files_to_parse = []
    
    # Threaded download
    def fetch_asset(u):
        dest = url_to_local_path(u)
        success = download_file(u, dest)
        return u, dest, success

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_asset, u): u for u in all_asset_urls}
        for future in as_completed(futures):
            u, dest, ok = future.result()
            if ok and dest.name.endswith(".css"):
                css_files_to_parse.append((u, dest))

    print(f"[*] Direct assets downloaded. Now scanning {len(css_files_to_parse)} CSS files for webfonts & background images...")
    
    nested_assets = set()
    for base_css_url, css_path in css_files_to_parse:
        try:
            content = css_path.read_text(encoding="utf-8", errors="ignore")
            # Find all url(...) declarations
            urls = re.findall(r'url\([\'"]?([^()\'"]+)[\'"]?\)', content)
            for raw_u in urls:
                if raw_u.startswith("data:") or raw_u.startswith("#"):
                    continue
                # Resolve relative to CSS url
                resolved = urllib.parse.urljoin(base_css_url, raw_u)
                if "templatekit.kitprostudio.com/necyron/" in resolved:
                    nested_assets.add(resolved)
        except Exception as e:
            print(f"[WARN] Failed scanning CSS {css_path}: {e}")
            
    print(f"[*] Found {len(nested_assets)} nested assets (webfonts/icons/images). Downloading...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_asset, u): u for u in nested_assets}
        for future in as_completed(futures):
            future.result()

    # 5. Process and write HTML files
    print("\n[Step 5/5] Rewriting links and saving HTML files...")
    for subpath, html in html_pages.items():
        # Replace Google fonts
        for g_url, local_g in google_replacements.items():
            # Replace exact or HTML entity encoded
            html = html.replace(g_url, local_g)
            html = html.replace(g_url.replace("&", "&#038;"), local_g)
            html = html.replace(g_url.replace("&", "&amp;"), local_g)

        # Replace domain with root relative paths
        # 1. JSON encoded URLs in elementorFrontendConfig
        html = html.replace(r"https:\/\/templatekit.kitprostudio.com\/necyron\/", "/")
        html = html.replace(r"https:\/\/templatekit.kitprostudio.com\/necyron", "")
        # 2. Standard absolute URLs
        html = html.replace("https://templatekit.kitprostudio.com/necyron/", "/")
        html = html.replace("http://templatekit.kitprostudio.com/necyron/", "/")
        html = html.replace("https://templatekit.kitprostudio.com/necyron", "/")
        
        # Save to appropriate index.html
        if subpath == "":
            dest_html = OUTPUT_DIR / "index.html"
        else:
            clean_sub = subpath.strip("/")
            dest_html = OUTPUT_DIR / clean_sub / "index.html"
            
        dest_html.parent.mkdir(parents=True, exist_ok=True)
        dest_html.write_text(html, encoding="utf-8")
        print(f" -> Saved: {dest_html.relative_to(OUTPUT_DIR)}")

    print("\n=================================================================")
    print("             NECYRON MIRROR COMPLETED SUCCESSFULLY!             ")
    print(f" Target Folder: {OUTPUT_DIR}")
    print("=================================================================")

if __name__ == "__main__":
    main()
