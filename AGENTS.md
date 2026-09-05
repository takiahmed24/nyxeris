# Nyxeris Project & Multi-Agent Collaboration Guide

> **Note for AI Agents**: Multiple Antigravity agents may be operating simultaneously on this repository across parallel subscription instances. Always follow the synchronization protocol below so all instances stay aligned and "know all things".

---

## 🤝 Parallel Multi-Agent Synchronization Protocol

1. **Shared State Ledger (`PROJECT_STATE.md`)**:
   - Before starting complex modifications, check `PROJECT_STATE.md` to see recent work completed by your peer agent and active tasks.
   - When completing significant work, creating endpoints, modifying schema, or making architectural decisions, **append an entry to `PROJECT_STATE.md`**.
2. **Atomic File Safety**:
   - Never overwrite large files indiscriminately; use targeted search-and-replace edits.
   - Run `python -m py_compile` on any modified Python files to prevent syntax errors that could block the other agent.
3. **One-Click Launchers**:
   - All services, dashboards, or parallel launchers must have a single-click `.bat` launcher in the project root.
4. **Mandatory Local-First AI Execution**:
   - Both agents must prioritize local models via Ollama (`http://localhost:11434`) first for all local processing tasks:
     - Text/Reasoning: `titan-one:latest` (Qwen2 7.6B)
     - Vision/OCR: `qwen2.5vl:3b` (3.8B Vision)
     - Vector Embeddings: `nomic-embed-text:latest`
   - Reserve cloud subscription quotas strictly for tasks that require cloud Gemini capabilities.

---

## 🏛️ Project Architecture & Stack

- **Project**: Nyxeris Storefront & Payment Engine
- **Core Framework**: FastAPI (`main.py`)
- **Database**: SQLite (`database.py`, `data/nyxeris.db`)
- **Payment & Checkout**: Whop integration with white-labeled receipt and order delivery
- **Frontend / Aesthetics**:
  - Jinja2 templates (`templates/`) & Static assets (`static/`)
  - Submodules / Sister sites: `necyron/`, `nexteuv/`, `whop_cj_app/`
  - **Design System**: Shopify Pipeline Theme (Editorial Luxury)
    - Aesthetics: Refined, minimalist editorial retail. Pure White canvas (`#ffffff`), elevated off-white surfaces (`#f7f5f4`), deep rich dark text (`#1f1919`).
    - Typography: Editorial Serif (`'Libre Baskerville'`) for titles/headings, clean sans (`'Poppins'`) for body, `'Montserrat'` for navigation.
    - Accents & Structure: Sharp micro-radius (`border-radius: 2px`), subtle hairline borders (`#e8e8e8`).
    - Zero Glassmorphism: NO frosted glass (`backdrop-filter`), NO neon cyan, NO glowing gradients.

---

## 📂 Key Directory Layout

- `main.py`: Main FastAPI entrypoint, middleware, and route registrations.
- `config.py`: Settings, environment paths, API keys, and configurations.
- `database.py`: SQLite schema definitions, orders, products, sessions.
- `routes/`:
  - `store_routes.py`: Storefront product views, catalog, checkout endpoints.
  - `webhook_routes.py`: Whop webhooks and event listeners.
  - `admin_routes.py`: Admin dashboard and management tools.
  - `auth_routes.py`: Authentication and admin session management.
- `services/`: Background processing, notifications, fulfillment logic.
- `scripts/`: Maintenance, migration, and automation utilities.
- `templates/` & `static/`: HTML templates and CSS/JS styling.
