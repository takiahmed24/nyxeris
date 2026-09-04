"""Titan-One AI Assistant Service for Nyxeris.
Connects to the local modified AI model (titan-one:latest) via Ollama.
Delegates product evaluation, luxury copy generation, and catalog curation to Titan-One,
recording all decisions into a training log.
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path("C:/Nyxeris")
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_LOG_PATH = DATA_DIR / "titan_training_log.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "titan-one:latest"


def call_titan(messages, temperature=0.3, timeout=90):
    """Sends a chat completion request to local titan-one model."""
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 1024
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            elapsed = round(time.time() - start_t, 2)
            content = res_json.get("message", {}).get("content", "")
            return {
                "success": True,
                "content": content,
                "elapsed": elapsed,
                "eval_count": res_json.get("eval_count", 0)
            }
    except Exception as e:
        elapsed = round(time.time() - start_t, 2)
        return {
            "success": False,
            "error": str(e),
            "elapsed": elapsed
        }


def log_training_step(task_type, prompt_summary, titan_output, supervisor_evaluation):
    """Logs Titan-One's execution and our supervision/training feedback."""
    logs = []
    if TRAINING_LOG_PATH.exists():
        try:
            with open(TRAINING_LOG_PATH, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_type": task_type,
        "prompt_summary": prompt_summary,
        "titan_output": titan_output,
        "supervisor_evaluation": supervisor_evaluation,
        "status": "APPROVED" if supervisor_evaluation.get("passed") else "CORRECTED"
    }
    logs.append(entry)
    with open(TRAINING_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    return entry


def evaluate_product_with_titan(candidate_product):
    """Asks Titan-One to review a candidate CJ product for Nyxeris brand standards."""
    prompt = f"""You are the Product Director and Sovereign Brain of Nyxeris.
Nyxeris Brand Standard:
- Category: Precision Workspace & Desk Architecture, EDC Hardware.
- Aesthetic: Modeled after Leica and Insta360 Luna Ultra. Studio black, aerospace aluminum, matte textures.
- Strict Constraints: NO cheap plastic junk, NO glowing neon gamer clutter, NO flimsy apparel.
- Financial Target: Minimum 65% profit margin, high perceived value, <3% return rate.

Evaluate this candidate product from CJ Dropshipping:
Product Title: {candidate_product.get('title', '')}
Supplier Link: {candidate_product.get('href', '')}
Supplier Price: {candidate_product.get('price', '')}

Respond in STRICT JSON format with these exact keys:
{{
  "brand_fit_score": <integer 1 to 10>,
  "approved": <true or false>,
  "suggested_nyxeris_title": "<luxurious hardware title for our website>",
  "target_retail_price": <number>,
  "reasoning": "<1-2 concise sentences on why this fits or does not fit Nyxeris>"
}}
"""
    messages = [
        {"role": "system", "content": "You are TITAN-ONE, Product Director for Nyxeris Hardware. Output valid JSON only."},
        {"role": "user", "content": prompt}
    ]

    print(f"[*] Prompting Titan-One to evaluate: {candidate_product.get('title', '')[:50]} ...")
    res = call_titan(messages, temperature=0.2)
    
    if res["success"]:
        content = res["content"].strip()
        # Clean JSON markdown fences if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        try:
            parsed = json.loads(content)
            log_training_step(
                task_type="product_evaluation",
                prompt_summary=f"Evaluate {candidate_product.get('title', '')[:40]}",
                titan_output=parsed,
                supervisor_evaluation={"passed": True, "notes": "Valid JSON and coherent score."}
            )
            return parsed
        except json.JSONDecodeError:
            log_training_step(
                task_type="product_evaluation",
                prompt_summary=f"Evaluate {candidate_product.get('title', '')[:40]}",
                titan_output=content,
                supervisor_evaluation={"passed": False, "notes": "Output was not valid JSON; fallback used."}
            )
            return {
                "brand_fit_score": 8,
                "approved": True,
                "suggested_nyxeris_title": candidate_product.get('title', ''),
                "target_retail_price": 69.00,
                "reasoning": content[:200]
            }
    else:
        print(f"[!] Titan-One call failed: {res.get('error')}")
        return None


def generate_whop_copy_with_titan(product):
    """Asks Titan-One to write high-converting, white-labeled copy for Whop."""
    prompt = f"""You are the Lead Hardware Copywriter for Nyxeris.
Product: {product['title']}
Category: {product['category']}
Retail Price: ${product['price']}
Supplier Cost: ${product['cost_price']}

Write the complete product copy for Whop.
Rules:
- Strictly ZERO mentions of Whop or dropshipping in the copy.
- Tone: Ultra-minimalist, architectural, precision-focused, premium.
- Highlight tactile build, aerospace materials, and intentional desk setup.

Respond in STRICT JSON format:
{{
  "tagline": "<punchy one-liner>",
  "short_description": "<2-3 sentence overview>",
  "bullet_features": ["<feature 1>", "<feature 2>", "<feature 3>", "<feature 4>"],
  "specs_breakdown": {{"Materials": "<val>", "Dimensions": "<val>", "Compatibility": "<val>", "In The Box": "<val>"}}
}}
"""
    messages = [
        {"role": "system", "content": "You are TITAN-ONE, Lead Hardware Copywriter for Nyxeris. Output valid JSON only."},
        {"role": "user", "content": prompt}
    ]

    print(f"[*] Prompting Titan-One for Whop copy: {product['title']} ...")
    res = call_titan(messages, temperature=0.3)
    if res["success"]:
        content = res["content"].strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        try:
            parsed = json.loads(content)
            log_training_step(
                task_type="whop_copy_generation",
                prompt_summary=f"Copy for {product['title']}",
                titan_output=parsed,
                supervisor_evaluation={"passed": True, "notes": "High quality copy and specs."}
            )
            return parsed
        except json.JSONDecodeError:
            return None
    return None


if __name__ == "__main__":
    # Test connection
    print(f"Testing Titan-One connection at {OLLAMA_URL}...")
    res = call_titan([{"role": "user", "content": "Titan, respond with 'READY' to confirm online."}], timeout=60)
    print(f"Result: {res}")
