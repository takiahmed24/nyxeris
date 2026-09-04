import re
from pathlib import Path

for filename in ["onsus_home05.html", "onsus_home01.html"]:
    p = Path(r"c:\Nyxeris\templates") / filename
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    
    # Replace any /static/onsus/external/fonts.googleapis.com/... with clean Google Fonts link
    # or keep the clean Google Fonts href so it loads fonts smoothly
    def repl_font(m):
        raw = m.group(0)
        # restore https://fonts.googleapis.com/css?family=...
        m2 = re.search(r'family=([^"\']+)', raw)
        if m2:
            fam = m2.group(1).replace(".dat", "").replace("&amp;", "&")
            return f'<link rel="stylesheet" href="https://fonts.googleapis.com/css?family={fam}"'
        return raw

    new_text = re.sub(r'<link[^>]+href=[\'"][^\'"]*fonts\.googleapis\.com[^\'"]*[\'"]', repl_font, text)
    
    # Also clean up any corrupted hrefs that have `:` or `|` or `.dat` in the static path
    p.write_text(new_text, encoding="utf-8")
    print(f"[OK] Cleaned font links in {filename}")
