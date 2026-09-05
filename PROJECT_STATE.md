# Nyxeris Real-Time Project State & Shared Agent Memory

> **Purpose**: This file serves as the continuous synchronization bridge between parallel Antigravity instances. Whenever either instance completes a task, modifies code, or changes system architecture, log it here so the other instance immediately knows.

---

## ⚡ Active Agent Workstreams

| Agent / Instance | Current Focus | Status | Active Files |
| :--- | :--- | :--- | :--- |
| **Instance 1 (Primary)** | Active (Account 1) | Managing Store & Architecture | `C:\Nyxeris` |
| **Instance 2 (Secondary)** | Active (Account 2 - Spawned) | Ready for Auth & Manual Failover | `C:\Nyxeris` / `C:\Antigravity` |

---

## 📋 Recent Changes & Architectural Log

* **[2026-09-05] 1,024 Catalog Scale & Live Whop ID Synchronization**:
  * Scaled physical product catalog in `data/nyxeris.db` to 1,024 items across 5 departments.
  * Extracted and mapped all 1,024 official live Whop Product IDs (`prod_...`) and Plan checkout URLs (`plan_...`) directly from Whop's master export (`data/nyxeris_full_1024_catalog_mapping_FINAL.csv`).
  * Updated `data/whop_id_mapping.json`, `data/nyxeris_1000_catalog.json`, and `data/whop_1000_products_catalog.csv`.
  * Reverse-engineered the complete Whop API 5-step pipeline (80-character title limit, batching by 125, CDN image polling, one-time plans).
  * Built `services/whop_catalog_sync.py` for 1-click autonomous catalog syncing.
  * Registered `skill_whop_bulk_catalog_sync` into `data/titan_skills_library.json` for local AI `titan-one:latest`.
* **[2026-09-05] Parallel Instance Setup**:
  * Created `start_antigravity_account2.bat` and `start_antigravity_ide_account2.bat` using `--user-data-dir` for multi-subscription parallelism.
  * Initialized `AGENTS.md` and `GEMINI.md` to establish project-wide memory and multi-agent protocols.
  * Initialized `PROJECT_STATE.md` as the live shared ledger.

---

## 🧭 System Overview & Key Endpoints

* **Storefront**: FastAPI serving Nyxeris products with Whop checkout.
* **Database**: SQLite database at `data/nyxeris.db`.
* **Port**: Default runs on port `8000` (`http://localhost:8000`).
* **Sub-Apps**:
  * Necyron: `/necyron`
  * NextEUV: `serve_nexteuv.py`
  * CJ/Whop Bridge: `start_cj_whop_bridge.bat`

---

## 📌 Upcoming / Pending Tasks

- [ ] Connect and test second Antigravity instance.
- [ ] Any upcoming storefront, dropshipping, or payment feature tasks requested by the user.
