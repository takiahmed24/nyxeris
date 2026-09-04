"""Lightweight local HTTP server for Necyron Offline Website.

Supports clean WordPress/Elementor URL routing, directory index resolution,
correct webfont/SVG MIME types, and mock handlers for WordPress AJAX/REST APIs.
"""

import sys
import os
import json
import mimetypes
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

# Ensure proper MIME mappings for modern web assets
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/woff", ".woff")
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("application/vnd.ms-fontobject", ".eot")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/webp", ".webp")

SITE_DIR = Path(__file__).resolve().parent

class NecyronHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def end_headers(self):
        # Enable CORS and caching headers
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        """Mock handler for contact form submissions and Elementor AJAX pings."""
        parsed = urllib.parse.urlparse(self.path)
        if "admin-ajax.php" in parsed.path or "/wp-json/" in parsed.path or "jkit-ajax-request" in parsed.query:
            response_data = json.dumps({"success": True, "status": "ok", "message": "Submission received locally."}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        else:
            self.send_response(200)
            self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = urllib.parse.unquote(parsed.path)

        # Handle mock AJAX or WP-JSON endpoints on GET
        if "admin-ajax.php" in clean_path or "/wp-json/" in clean_path:
            response_data = json.dumps({"success": True, "status": "ok"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
            return

        # Resolve clean paths to index.html
        local_rel = clean_path.lstrip("/")
        target_path = (SITE_DIR / local_rel).resolve()

        # Check if target is inside SITE_DIR
        try:
            target_path.relative_to(SITE_DIR)
        except ValueError:
            self.send_error(403, "Access Denied")
            return

        # If it's a directory, check for index.html
        if target_path.is_dir():
            index_file = target_path / "index.html"
            if index_file.is_file():
                self.serve_file(index_file)
                return

        # If clean URL without trailing slash matches a directory
        if not target_path.exists() and (SITE_DIR / local_rel / "index.html").is_file():
            self.serve_file(SITE_DIR / local_rel / "index.html")
            return

        # If exact file exists
        if target_path.is_file():
            self.serve_file(target_path)
            return

        # Fallback to 404 page
        not_found_file = SITE_DIR / "template-kit" / "404" / "index.html"
        if not_found_file.is_file():
            self.send_response(404)
            data = not_found_file.read_bytes()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        super().do_GET()

    def serve_file(self, file_path: Path):
        try:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "application/octet-stream"
            if mime_type.startswith("text/") or mime_type in ("application/javascript", "application/json"):
                mime_type += "; charset=utf-8"

            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

def run(port: int = 8080):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, NecyronHandler)
    print("=" * 70)
    print("       NECYRON LOCAL WEBSITE SERVER - 100% OFFLINE EDITION       ")
    print("=" * 70)
    print(f"[*] Serving Necyron from: {SITE_DIR}")
    print(f"[*] Local URL: http://localhost:{port}")
    print(f"[*] Press CTRL+C to stop the server.")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")
        httpd.server_close()

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port)
