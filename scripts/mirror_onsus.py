"""
Mirror Onsus WordPress theme pages (Home 05 and Home 01) and all associated assets.
Saves all stylesheets, scripts, images, and fonts locally under static/onsus/
and rewrites templates for complete offline local execution.
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure unbuffered output
sys.stdout.reconfigure(line_buffering=True)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ONSUS_DIR = BASE_DIR / "static" / "onsus"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_ONSUS_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

TARGET_PAGES = {
    "onsus_home05.html": "https://oneuswp.themesflat.com/home-05/",
    "onsus_home01.html": "https://oneuswp.themesflat.com/"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

session = requests.Session()
session.headers.update(HEADERS)

def sanitize_filename(filename: str) -> str:
    clean = filename.split("?")[0].split("#")[0]
    clean = re.sub(r'[<>:"|?*]', '_', clean)
    return clean

def get_local_path_for_url(url: str, base_url: str = "https://oneuswp.themesflat.com/") -> tuple[Path, str]:
    """Returns (disk_path, web_url_path)."""
    full_url = urljoin(base_url, url)
    parsed = urlparse(full_url)
    clean_path = unquote(parsed.path).lstrip("/")
    
    # Handle domain
    if parsed.netloc in ("oneuswp.themesflat.com", "www.oneuswp.themesflat.com", ""):
        rel_path = clean_path
    else:
        domain_folder = re.sub(r'[<>:"/\\|?*]', '_', parsed.netloc)
        rel_path = f"external/{domain_folder}/{clean_path}"
        
    parts = rel_path.split("/")
    if not parts or parts[-1] == "" or "." not in parts[-1]:
        fname = sanitize_filename(parsed.query) or "asset"
        if not fname.endswith(".html"):
            fname += ".dat"
        parts.append(fname)
    else:
        parts[-1] = sanitize_filename(parts[-1])
        
    rel_file_path = Path(*parts)
    disk_path = STATIC_ONSUS_DIR / rel_file_path
    web_path = "/static/onsus/" + "/".join(parts)
    return disk_path, web_path

def download_file(url: str, disk_path: Path) -> bool:
    if disk_path.exists() and disk_path.stat().st_size > 0:
        return True
    try:
        disk_path.parent.mkdir(parents=True, exist_ok=True)
        resp = session.get(url, timeout=6, stream=True)
        if resp.status_code == 200:
            with open(disk_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            return False
    except Exception:
        return False

def scan_css_for_assets(css_content: str, css_url: str) -> list[str]:
    urls = []
    matches = re.findall(r'url\s*\(\s*[\'"]?([^\'")]+)[\'"]?\s*\)', css_content, re.IGNORECASE)
    for m in matches:
        m = m.strip()
        if m.startswith("data:") or m.startswith("#"):
            continue
        full = urljoin(css_url, m)
        urls.append(full)
    imports = re.findall(r'@import\s+[\'"]([^\'"]+)[\'"]', css_content, re.IGNORECASE)
    for imp in imports:
        imp = imp.strip()
        if not imp.startswith("data:"):
            urls.append(urljoin(css_url, imp))
    return list(set(urls))

def mirror_page(template_filename: str, page_url: str):
    out_file = TEMPLATES_DIR / template_filename
    print(f"\n========================================================", flush=True)
    print(f"[*] Mirroring: {page_url} -> {template_filename}", flush=True)
    print(f"========================================================", flush=True)
    
    resp = session.get(page_url, timeout=15)
    resp.raise_for_status()
    html_content = resp.text

    soup = BeautifulSoup(html_content, "html.parser")
    
    css_to_download = []
    js_to_download = []
    images_to_download = []
    
    # 1. Stylesheets
    for link in soup.find_all("link", rel=lambda r: r and "stylesheet" in r):
        href = link.get("href")
        if href and not href.startswith("data:"):
            full_url = urljoin(page_url, href)
            disk_path, web_path = get_local_path_for_url(full_url, page_url)
            css_to_download.append((full_url, disk_path))
            link["href"] = web_path

    # Favicons
    for link in soup.find_all("link", rel=lambda r: r and any(x in r for x in ["icon", "apple-touch-icon"])):
        href = link.get("href")
        if href and not href.startswith("data:"):
            full_url = urljoin(page_url, href)
            disk_path, web_path = get_local_path_for_url(full_url, page_url)
            images_to_download.append((full_url, disk_path))
            link["href"] = web_path

    # 2. Scripts
    for script in soup.find_all("script", src=True):
        src = script.get("src")
        if src and not src.startswith("data:"):
            full_url = urljoin(page_url, src)
            disk_path, web_path = get_local_path_for_url(full_url, page_url)
            js_to_download.append((full_url, disk_path))
            script["src"] = web_path

    # 3. Images and Picture sources
    for img in soup.find_all("img"):
        for attr in ["src", "data-src", "data-lazy-src", "data-orig-src"]:
            src = img.get(attr)
            if src and not src.startswith("data:"):
                full_url = urljoin(page_url, src)
                disk_path, web_path = get_local_path_for_url(full_url, page_url)
                images_to_download.append((full_url, disk_path))
                img[attr] = web_path
                
        srcset = img.get("srcset")
        if srcset:
            parts = []
            for item in srcset.split(","):
                item = item.strip()
                if not item:
                    continue
                tokens = item.split()
                if tokens:
                    s_url = tokens[0]
                    s_desc = " ".join(tokens[1:]) if len(tokens) > 1 else ""
                    if not s_url.startswith("data:"):
                        full_url = urljoin(page_url, s_url)
                        dpath, wpath = get_local_path_for_url(full_url, page_url)
                        images_to_download.append((full_url, dpath))
                        parts.append(f"{wpath} {s_desc}".strip())
                    else:
                        parts.append(item)
            img["srcset"] = ", ".join(parts)

    for source in soup.find_all("source"):
        for attr in ["src", "data-src"]:
            src = source.get(attr)
            if src and not src.startswith("data:"):
                full_url = urljoin(page_url, src)
                disk_path, web_path = get_local_path_for_url(full_url, page_url)
                images_to_download.append((full_url, disk_path))
                source[attr] = web_path
        srcset = source.get("srcset")
        if srcset:
            parts = []
            for item in srcset.split(","):
                item = item.strip()
                if not item:
                    continue
                tokens = item.split()
                if tokens:
                    s_url = tokens[0]
                    s_desc = " ".join(tokens[1:]) if len(tokens) > 1 else ""
                    if not s_url.startswith("data:"):
                        full_url = urljoin(page_url, s_url)
                        dpath, wpath = get_local_path_for_url(full_url, page_url)
                        images_to_download.append((full_url, dpath))
                        parts.append(f"{wpath} {s_desc}".strip())
                    else:
                        parts.append(item)
            source["srcset"] = ", ".join(parts)

    # 4. Background images in inline styles
    for tag in soup.find_all(style=True):
        style = tag.get("style", "")
        bg_matches = re.findall(r'url\([\'"]?([^\'")]+)[\'"]?\)', style)
        for bg in bg_matches:
            bg = bg.strip()
            if not bg.startswith("data:"):
                full_url = urljoin(page_url, bg)
                disk_path, web_path = get_local_path_for_url(full_url, page_url)
                images_to_download.append((full_url, disk_path))
                style = style.replace(bg, web_path)
        tag["style"] = style

    # Rewrite navigation links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "oneuswp.themesflat.com/home-05" in href:
            a["href"] = "/home-05"
        elif "oneuswp.themesflat.com/home-01" in href:
            a["href"] = "/home-01"
        elif href in ("https://oneuswp.themesflat.com", "https://oneuswp.themesflat.com/", "https://oneuswp.themesflat.com/?storefront=envato-elements"):
            a["href"] = "/"
        elif href.startswith("https://oneuswp.themesflat.com"):
            parsed = urlparse(href)
            path = parsed.path
            a["href"] = f"/#browse{path.replace('/', '-')}"

    # Download in parallel
    all_downloads = list(set(css_to_download + js_to_download + images_to_download))
    print(f"[*] Total unique assets to download for {template_filename}: {len(all_downloads)}", flush=True)
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(download_file, url, disk): url for url, disk in all_downloads}
        completed = 0
        for fut in as_completed(futures):
            completed += 1
            if completed % 50 == 0 or completed == len(all_downloads):
                print(f"  Downloaded {completed}/{len(all_downloads)} assets...", flush=True)

    # Collect nested assets from all CSS files and download in parallel
    print("[*] Scanning and downloading nested CSS fonts and background assets...", flush=True)
    nested_css_assets = []
    for url, disk in set(css_to_download):
        if disk.exists():
            try:
                text = disk.read_text(encoding="utf-8", errors="ignore")
                found = scan_css_for_assets(text, url)
                for f_url in found:
                    dpath, wpath = get_local_path_for_url(f_url, url)
                    nested_css_assets.append((f_url, dpath))
                
                # Rewrite absolute URLs
                new_text = re.sub(r'https?://(?:www\.)?oneuswp\.themesflat\.com/', '/static/onsus/', text)
                new_text = re.sub(r'//(?:www\.)?oneuswp\.themesflat\.com/', '/static/onsus/', new_text)
                disk.write_text(new_text, encoding="utf-8")
            except Exception:
                pass

    unique_nested = list(set(nested_css_assets))
    print(f"[*] Found {len(unique_nested)} nested assets in CSS. Downloading...", flush=True)
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(download_file, url, disk): url for url, disk in unique_nested}
        completed = 0
        for fut in as_completed(futures):
            completed += 1
            if completed % 50 == 0 or completed == len(unique_nested):
                print(f"  Downloaded {completed}/{len(unique_nested)} nested assets...", flush=True)

    # Clean up HTML text for any remaining absolute links
    html_output = str(soup)
    html_output = re.sub(r'https?://(?:www\.)?oneuswp\.themesflat\.com/wp-content/', '/static/onsus/wp-content/', html_output)
    html_output = re.sub(r'https?://(?:www\.)?oneuswp\.themesflat\.com/wp-includes/', '/static/onsus/wp-includes/', html_output)
    html_output = re.sub(r'//(?:www\.)?oneuswp\.themesflat\.com/wp-content/', '/static/onsus/wp-content/', html_output)
    html_output = re.sub(r'//(?:www\.)?oneuswp\.themesflat\.com/wp-includes/', '/static/onsus/wp-includes/', html_output)
    
    local_script_shim = """
    <script>
    /* Local Offline Shims for Onsus */
    window.wp = window.wp || {};
    window.wc_cart_fragments_params = {
        wc_ajax_url: '/api/wc-ajax',
        cart_hash_key: 'onsus_wc_cart_hash',
        fragment_name: 'onsus_wc_fragments'
    };
    window.wc_add_to_cart_params = {
        wc_ajax_url: '/api/wc-ajax',
        i18n_view_cart: 'View Cart',
        cart_url: '#cart',
        is_cart: '',
        cart_redirect_after_add: 'no'
    };
    window.themesflat_ajax = {
        ajaxurl: '/api/tf-ajax',
        nonce: 'local_nonce'
    };
    </script>
    """
    if "</head>" in html_output:
        html_output = html_output.replace("</head>", f"{local_script_shim}\n</head>")

    out_file.write_text(html_output, encoding="utf-8")
    print(f"[OK] Saved mirrored page to {out_file} ({len(html_output)} bytes)", flush=True)

def main():
    print("==================================================", flush=True)
    print("  ONSUS E-COMMERCE FULL LOCAL MIRROR ENGINE", flush=True)
    print("==================================================", flush=True)
    for filename, url in TARGET_PAGES.items():
        mirror_page(filename, url)
    print("\n[OK] All pages and assets mirrored successfully!", flush=True)

if __name__ == "__main__":
    main()
