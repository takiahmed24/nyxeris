import re
from pathlib import Path
import requests

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

# 1. Download missing assets if needed
missing = [
    ("https://oneuswp.themesflat.com/wp-content/themes/onsus/images/bg-actionbox.jpg", Path(r"c:\Nyxeris\static\onsus\wp-content\themes\onsus\images\bg-actionbox.jpg")),
    ("https://oneuswp.themesflat.com/wp-content/plugins/yith-woocommerce-wishlist/assets/images/ajax-loader-alt.svg", Path(r"c:\Nyxeris\static\onsus\wp-content\plugins\yith-woocommerce-wishlist\assets\images\ajax-loader-alt.svg"))
]

for url, disk in missing:
    try:
        disk.parent.mkdir(parents=True, exist_ok=True)
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            disk.write_bytes(r.content)
            print(f"[OK] Downloaded {url} -> {disk.name}")
    except Exception as e:
        print(f"[WARN] Failed {url}: {e}")

# 2. Fix trailing punctuation in templates
for fname in ["onsus_home05.html", "onsus_home01.html"]:
    p = Path(r"c:\Nyxeris\templates") / fname
    if p.exists():
        t = p.read_text(encoding="utf-8", errors="ignore")
        t = t.replace("/static/onsus/wp-content/themes/onsus/images/bg-actionbox.jpg);}", "/static/onsus/wp-content/themes/onsus/images/bg-actionbox.jpg")
        p.write_text(t, encoding="utf-8")
        print(f"[OK] Cleaned url artifacts in {fname}")
