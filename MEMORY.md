# Project Memory & Architecture Context

## Project Identity
- **Project Name:** AI Trading Copilot
- **Full Title:** AI Trading Copilot — Intelligent Trading Analytics, Risk Management & Decision Support System
- **Core Vision:** "The AI should understand the trader, not just the market."
- **Academic Context:** Final Year Project (FYP) & Professional FinTech SaaS Foundation.

---

## 1. System Snapshot & Environment Audit

### 1.1 Verified Host Environment (Audited 2026-10-02)
- **Operating System:** Windows 11 (64-bit)
- **Python Runtime:** Python 3.12.10 (Installed & operational)
- **Node.js Runtime:** Node.js v22.17.0 (Installed & operational)
- **Package Manager:** npm 11.6.4
- **MetaTrader 5 Terminal:** Physically verified at `C:\Program Files\MetaTrader 5\terminal64.exe` (`Test-Path` returned `True`)
- **Docker / PostgreSQL CLI:** `docker` and `psql` are not currently in the Windows system `PATH`.
  - *Implication:* PostgreSQL will either be run via a native Windows service installation, a lightweight local installer, or a free cloud provider (e.g. Supabase / Neon) for pgvector, with SQLite available as a lightweight local unit testing fallback.
- **Git Status:** Clean initialized git repository at `d:\SMIT_Final_Project`, branch `master`, no commits yet.

### 1.2 Agent Development Skills Status
- **Builtin Skills Available:**
  - `agy-customizations`
  - `antigravity-guide`
- **Third-Party / Design Skills Checked:**
  - `UI/UX Pro Max`: Not installed in environment. (Not assumed).
  - `Tasty` / `Taste-related`: Not installed in environment. (Not assumed).
- **Rule Adherence:** We rely on our comprehensive `DESIGN.md` specification, shadcn/ui, Radix UI primitives, Lucide Icons, and Tailwind CSS tokens rather than unverified external skills. No packages installed without explicit user approval.

---

## 2. Key Architecture & Technical Decisions

1. **MT5 Integration Strategy (Option A - Windows IPC):**
   - We utilize the official `MetaTrader5` Python package connecting directly to the running `terminal64.exe` on the host machine.
   - Tested & supported for both **Live and Demo** accounts across any broker.
   - Strictly **read-only**: No trade execution, modification, or cancellation permissions requested.
   - Encrypted investor passwords using AES-256-GCM.
2. **Deal Aggregation & Position Lifecycle:**
   - Single MT5 deals (in/out/partial close) are grouped by `position_ticket` into single, unified `journal_entries` records.
   - Volume-weighted prices are computed for partial closes to guarantee mathematically accurate P&L and win/loss rates.
   - Idempotency hashes generated from `(account_id, position_id, deal_tickets_hash)` eliminate duplicates on repeated synchronization.
3. **Resilient Data Ingestion Fallback:**
   - CSV / HTML trade report import parser and manual trade entry modal ensure the system remains 100% operational even without a running MT5 terminal.
4. **Zero-Hallucination Deterministic Math:**
   - Financial calculations (Net P&L, Win Rate, Profit Factor, Expectancy, Max Drawdown) are computed exclusively by NumPy/Pandas in Python backend code.
   - LLMs are strictly forbidden from performing arithmetic or generating financial statistics.
5. **Mandatory Visual Distinction Badges:**
   - Every metric, summary, or observation rendered in the UI or emitted by the AI is tagged with:
     - `[VERIFIED DATA]`
     - `[CALCULATED METRICS]`
     - `[HISTORICAL STATISTICS]`
     - `[ML ESTIMATES]`
     - `[AI INTERPRETATION]`
6. **Stateful AI Decision Support via LangGraph & pgvector:**
   - Predictable DAG workflow: `Input Validation -> Risk Analysis -> Strategy RAG -> Behavioral Rules -> Structured Synthesis -> Badge Tagging`.
   - Tenant-isolated RAG: Users query only their own uploaded trading playbooks and checklists.
   - System prompts protect against prompt injection from user-uploaded PDF/text documents.
7. **Independence from Paid Services & n8n:**
   - Core application runs autonomously on native FastAPI background tasks and local PostgreSQL.
   - n8n is strictly an optional notification tool for Telegram/Discord, never placed on the critical backend path.

---

## 3. UI/UX Strategy & Component Ecosystem

- **Theme:** High-density, institutional Dark Mode (`#080B11` obsidian slate canvas, `#0E131F` card surfaces).
- **Component Primitives:** shadcn/ui + Radix UI headless components.
- **Icons:** Lucide Icons.
- **Data Visualization:** Recharts for financial curves and breakdown charts; TradingView Lightweight Charts for candlestick analysis.
- **Micro-Interactions:** Subtle Framer Motion transitions (layoutId, tab switches, modal fades) respecting `prefers-reduced-motion`.
- **Component Restraint:** GSAP and Lenis avoided in the dashboard to ensure native scroll accessibility and maximum rendering performance.

---

## 4. Current Project State

- **Current Mode:** IMPLEMENTATION (Phase 1 — Foundation Completed).
- **Completed Work:**
  - **TASK-000:** Complete Documentation Suite (PRD, ARCHITECTURE, RULES, DESIGN, TASKS, MEMORY).
  - **TASK-001: Backend Service Scaffolding:**
    - Python 3.12 virtual environment in `backend/.venv`.
    - FastAPI ASGI application with Pydantic v2 settings management.
    - Structured logging with secret masking filter (`SecretMaskingFilter`).
    - Custom typed error handling and standard JSON error response schemas.
    - SQLAlchemy 2.0 async engine and session factory (`session.py`).
    - Base declarative models with UTC timestamp and tenant isolation mixins.
    - Health endpoint `/api/v1/health` verifying database connectivity and host MT5 terminal presence.
    - Pytest test suite: 4 tests passed in 0.29s (`test_health.py`, `test_errors.py`).
    - Ruff linting and formatting: 100% clean.
  - **TASK-002: Frontend Workspace Scaffolding:**
    - Next.js 14+ App Router with strict TypeScript (`frontend/`).
    - Tailwind CSS with institutional obsidian slate FinTech design tokens (`globals.css`, `tailwind.config.ts`).
    - Utility `cn` helper for class merging (`utils.ts`).
    - `Badge` component with mandatory visual classification variants (`[VERIFIED DATA]`, `[CALCULATED METRICS]`, etc.).
    - Responsive `Sidebar` navigation and diagnostic `Header` with account switcher and sync triggers.
    - Executive dashboard layout with Recharts equity curve and behavioral guard indicators.
    - Eslint verification: `✔ No ESLint warnings or errors`.
    - Production build verification: `npm run build` compiled successfully (5/5 static routes prerendered).
  - **Security & Secret Hygiene:**
    - Comprehensive `.gitignore` created.
    - Zero secrets committed.
- **Exact Next Task (according to TASKS.md):** **TASK-003: PostgreSQL & pgvector Schema Setup with Alembic** (Phase 2).
- **Stop Condition:** Stopped after TASK-001 and TASK-002. Awaiting user instruction before starting TASK-003.

---

## 5. Technical Risks & Mitigations

| Risk | Description | Mitigation Strategy |
| :--- | :--- | :--- |
| **MT5 Terminal Dependency** | Option A requires a running Windows MT5 terminal. If the user runs the app on a Linux server without terminal, direct sync fails. | Robust CSV import and manual trade entry fallback ensure 100% feature availability without MT5. |
| **PostgreSQL & pgvector Setup** | Docker is not recognized on the host Windows machine. | Provide setup scripts for local Windows PostgreSQL installation, or connect to a free-tier hosted PostgreSQL instance (e.g. Supabase/Neon). SQLite with NumPy fallback used for unit tests. |
| **Partial Closes Data Integrity** | Retail brokers log multiple deals for scaled exits, which can distort win-rate calculations. | Implement volume-weighted deal aggregation service in `backend/services/mt5_sync.py` grouping deals by `position_id`. |
| **LLM Hallucination Risk** | LLM generating inaccurate risk assessments or fabricated prices. | Guardrails enforce deterministic Python math calculations first; LLM only consumes validated numerical context and must append uncertainty disclaimers. |
