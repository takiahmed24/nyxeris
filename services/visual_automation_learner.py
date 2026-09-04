"""Self-Learning Visual Automation Service for Nyxeris.
Connects Playwright CDP with local visual model qwen2.5vl:3b and titan-one.
Learns repeating browser patterns, catalogs UI states into visual memory,
and teaches the local models how to automate CJ Dropshipping and Whop operations.
"""

import os
import json
import time
from pathlib import Path
from services.local_vision import analyze_image_locally

BASE_DIR = Path("C:/Nyxeris")
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots" / "learning"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_FILE = DATA_DIR / "visual_learning_memory.json"


class VisualAutomationLearner:
    def __init__(self):
        self.memory = self._load_memory()

    def _load_memory(self):
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"patterns": {}, "history": []}
        return {"patterns": {}, "history": []}

    def _save_memory(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2)

    def learn_page_state(self, page, task_name, expected_goal):
        """Captures the screenshot, asks qwen2.5vl:3b to analyze the state,
        and records learned selectors and coordinates for future automated runs.
        """
        timestamp = int(time.time())
        screenshot_name = f"{task_name}_{timestamp}.png"
        screenshot_path = SCREENSHOTS_DIR / screenshot_name
        page.screenshot(path=str(screenshot_path))

        prompt = f"""You are training as an autonomous visual agent for Nyxeris e-commerce operations.
Task: {task_name}
Goal: {expected_goal}
Current URL: {page.url}

Analyze this interface:
1. Identify the current page layout and state.
2. What are the key action elements (buttons, inputs, cards) needed to achieve the goal?
3. Provide precise visual cues and suggested next actions.
"""
        print(f"[*] [Visual Learner] Teaching qwen2.5vl:3b on state: {task_name}...")
        start_t = time.time()
        vis_res = analyze_image_locally(str(screenshot_path), prompt=prompt)
        elapsed = round(time.time() - start_t, 2)

        learned_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task_name": task_name,
            "url": page.url,
            "screenshot": str(screenshot_path),
            "expected_goal": expected_goal,
            "visual_model_analysis": vis_res.get("analysis", "") if vis_res.get("success") else vis_res.get("error"),
            "elapsed_seconds": elapsed
        }

        # Store pattern
        self.memory.setdefault("history", []).append(learned_entry)
        self.memory.setdefault("patterns", {})[task_name] = {
            "last_seen_url": page.url,
            "last_learned_at": learned_entry["timestamp"],
            "summary": learned_entry["visual_model_analysis"][:200]
        }
        self._save_memory()

        print(f"[+] [Visual Learner] State learned in {elapsed}s and saved to visual memory.")
        return learned_entry

    def get_pattern(self, task_name):
        return self.memory.get("patterns", {}).get(task_name)


learner = VisualAutomationLearner()
