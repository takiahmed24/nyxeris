"""Local Vision Service using qwen2.5vl:3b via Ollama.
Runs 100% locally on the user's GPU/CPU with zero cloud credits.
Analyzes screenshots, UI modals, and product images.
"""

import json
import base64
import time
import urllib.request
from pathlib import Path

OLLAMA_GEN_URL = "http://127.0.0.1:11434/api/generate"
VISION_MODEL = "qwen2.5vl:3b"

def analyze_image_locally(image_path, prompt="Describe what is visible on this screen and any buttons or inputs.", timeout=60):
    """Sends a local screenshot to qwen2.5vl:3b for free local visual analysis."""
    path = Path(image_path)
    if not path.exists():
        return {"success": False, "error": f"Image file not found: {image_path}"}
    
    with open(path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    payload = {
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 512
        }
    }
    
    req = urllib.request.Request(
        OLLAMA_GEN_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = round(time.time() - start_t, 2)
            return {
                "success": True,
                "analysis": data.get("response", "").strip(),
                "elapsed": elapsed
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    test_img = Path("C:/Nyxeris/data/screenshots/whop_after_create.png")
    if test_img.exists():
        print(f"Testing local visual model {VISION_MODEL} on {test_img.name}...")
        res = analyze_image_locally(test_img, "What is the created product name and ID visible on the page?")
        print("Result:", res)
    else:
        print(f"Test image {test_img} not found.")
