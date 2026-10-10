# Product Requirements Document (PRD)

## Project Title
**AI Trading Copilot — Intelligent Trading Analytics, Risk Management & Decision Support System**

---

## 1. Executive Summary & Product Vision

### 1.1 Executive Summary
Retail traders, forex traders, and prop firm challenge participants face high failure rates (>90%) primarily due to emotional indiscipline, inconsistent risk sizing, rule violations, and poor post-trade analysis. Existing trading software focuses almost exclusively on charting, raw indicators, or simplistic historical spreadsheets.

**AI Trading Copilot** bridges this gap by acting as an objective, data-driven personal trading coach and decision-support system. It automatically ingests trades via MetaTrader 5 (MT5) or CSV fallbacks, computes 100% deterministic financial metrics, monitors proprietary risk rules in real-time, identifies behavioral flaws (e.g., revenge trading, overtrading), reviews chart screenshots using computer vision, and offers contextual AI feedback rooted in the trader’s personal playbook.

### 1.2 Product Vision
> **"The AI should understand the trader, not just the market."**

The platform combines the trader's historical performance, personal strategy rules, trading behavior, account restrictions, historical setups, and available chart information to provide deeply contextual analysis.

### 1.3 Core Principles & Guardrails
- **Decision-Support, Not Automated Execution:** The copilot advises and analyzes; it never places, modifies, or closes orders autonomously.
- **Deterministic Math First:** All financial metrics (P&L, win rate, drawdown, expectancy, Sharpe) are computed by deterministic Python code. AI is never used to do arithmetic or hallucinate financial statistics.
- **Read-Only MT5 Integration:** The system only monitors and ingests account data; it never requires or utilizes trading permissions.
- **Strict Data Distinction:** Every piece of information rendered to the user must be explicitly labeled as `[VERIFIED DATA]`, `[CALCULATED METRICS]`, `[HISTORICAL STATISTICS]`, `[ML ESTIMATES]`, or `[AI INTERPRETATION]`.
- **Absolute User Isolation:** Multi-tenant security ensures trading data, notes, and strategy documents are isolated at the database query layer.

---

## 2. Target Audience & User Personas

### 2.1 Target Audiences
1. **Prop Firm Traders:** Traders aiming to pass or maintain funded accounts with strict maximum and daily drawdown limits.
2. **Retail Forex & CFD Traders:** Discretionary traders executing on MT5 who struggle with emotional management and journaling consistency.
3. **Price Action & SMC/ICT Students:** Traders seeking objective validation of their structural analysis (order blocks, fair value gaps, liquidity sweeps).

### 2.2 User Personas

#### Persona A: "Prop Firm Challenger" — Alex, 26
- **Profile:** Trades EURUSD and NAS100 on an MT5 demo account attempting a $100k funded evaluation.
- **Pain Points:** Loses accounts due to trailing drawdown breaches, emotional revenge trading after 2 consecutive losses, and manual journaling fatigue.
- **Goals:** Automated real-time alerts when approaching daily drawdown thresholds, objective risk calculation before entering trades, and automated MT5 journaling.

#### Persona B: "Discretionary ICT Trader" — Sophia, 31
- **Profile:** Trades London and New York sessions using Smart Money Concepts (ICT).
- **Pain Points:** Inconsistent execution of trading rules, entering outside designated killzones, struggling to review chart screenshots against setups.
- **Goals:** Uploading chart screenshots to verify FVG and liquidity sweep alignments, receiving pre-trade risk checklists, and benchmarking win rates across specific setups.

#### Persona C: "Beginner Forex Learner" — Marcus, 21
- **Profile:** University student learning technical analysis and forex fundamentals.
- **Pain Points:** Overwhelmed by contradictory YouTube courses, jargon, and unrealistic "99% win-rate" signal scams.
- **Goals:** Accessing a structured, zero-hype educational curriculum and vetted educational resources.

---

## 3. User Journeys

### 3.1 MT5 Account Connection & Automated Journaling Journey
```
[User Registers / Logs In] 
       │
       ▼
[Navigates to "Accounts" -> "Add Account"]
       │
       ▼
[Selects "MetaTrader 5 Integration"] 
       │ (Reviews setup instructions, read-only requirement)
       ▼
[Enters Server, Account Login, Read-Only / Investor Password]
       │
       ▼
[Backend Validates Connection via Local MT5 Terminal Bridge]
       │
       ▼
[Historical Deals & Positions Synchronized Idempotently]
       │
       ▼
[Multi-Deal Positions Aggregated into Unified Journal Entries]
       │
       ▼
[Dashboard & Analytics Instantly Update with Calculated Metrics]
```

### 3.2 Pre-Trade Review Journey
```
[Trader Identifies Potential Setup on Chart]
       │
       ▼
[Opens AI Trade Reviewer / Pre-Trade Check]
       │
       ▼
[Inputs Symbol, Direction, Proposed Entry, SL, TP, Strategy]
       │
       ▼
[Optionally Uploads Chart Screenshot]
       │
       ▼
[System Runs Deterministic Risk Calculations (Risk $, Risk %, RR)]
       │
       ▼
[System Checks Active Account Prop Rules (Daily Drawdown Margin)]
       │
       ▼
[AI Evaluates Setup against Personal Strategy Playbook (RAG)]
       │
       ▼
[System Displays Structured Review with Visual Distinction Badges]
       │
       ▼
[Trader Executes on Terminal Themself (Platform does NOT trade)]
```

---

## 4. Functional Requirements (FR)

### 4.1 Authentication & User Management
- **FR-001 (Must):** User registration with email, password (bcrypt hashed), and optional display name.
- **FR-002 (Must):** JWT-based secure session management with access and refresh tokens.
- **FR-003 (Must):** Strict multi-tenant user isolation. Every database query must filter by `user_id`.
- **FR-004 (Should):** User preference management (account base currency, timezone, default risk parameters).

### 4.2 Trading Account Management
- **FR-005 (Must):** Support for multiple trading accounts per user (Live, Demo, Prop Firm Challenge, Prop Firm Funded).
- **FR-006 (Must):** Manual account creation (balance, currency, leverage, broker label).
- **FR-007 (Must):** Account switcher across all dashboard and journal views.
- **FR-008 (Must):** Account metadata display: Balance, Equity, Margin, Free Margin, Floating P&L, Last Sync Time, Connection Status.
- **FR-009 (Must):** Connection revocation and account deletion with complete data cleanup.

### 4.3 MT5 Integration & Synchronization
- **FR-010 (Must):** MT5 connection prototype supporting Windows-based terminal via official `MetaTrader5` Python library.
- **FR-011 (Must):** Strictly read-only connection. No trade placement, modification, or closure capabilities.
- **FR-012 (Must):** Support for both Live and Demo accounts across any MT5 broker.
- **FR-013 (Must):** Full historical trade backfill (positions, orders, deals).
- **FR-014 (Must):** Incremental synchronization for new deals and closed positions.
- **FR-015 (Must):** Idempotent ingestion pipeline preventing duplicate journal entries using unique broker deal/position ticket hashes.
- **FR-016 (Must):** Multi-deal aggregation: Group partial closes, scale-ins, and closing deals into a single coherent trade position record while maintaining raw deal history.
- **FR-017 (Must):** Error recovery and automatic reconnection logic on terminal restarts or network dropouts.
- **FR-018 (Must):** Manual sync trigger ("Sync Now") button in UI with real-time status and timestamps.

### 4.4 Fallback Ingestion (CSV & Manual)
- **FR-019 (Must):** CSV import parser supporting standard MT5 exported HTML/CSV trade reports.
- **FR-020 (Must):** CSV template download and mapping wizard for custom broker exports.
- **FR-021 (Must):** Manual trade entry modal for traders without MT5 or trading off-platform.
- **FR-022 (Must):** Full parity: Manually entered or CSV-imported trades must feed the exact same analytics and journal pipelines as MT5-synced trades.

### 4.5 Trading Journal
- **FR-023 (Must):** Structured trade entries recording: Ticket/ID, Symbol, Direction (Buy/Sell), Entry Price, Exit Price, Volume/Lots, Open Time, Close Time, Stop Loss, Take Profit, Realized P&L, Commission, Swap, Net P&L.
- **FR-024 (Must):** User annotations: Strategy tag, Setup tag, Session tag (Asian, London, NY AM, NY PM), Emotional state before/after, Notes, Chart screenshot attachments.
- **FR-025 (Must):** Advanced filtering by Date Range, Symbol, Direction, Strategy, Session, Outcome (Win/Loss/BE), and Account.
- **FR-026 (Must):** Detailed trade drawer/modal displaying trade lifecycle, deal breakdown (if partial close), execution metrics, and AI retrospective.

### 4.6 Deterministic Financial Analytics Engine
- **FR-027 (Must):** Backend calculation of key metrics using NumPy/Pandas:
  - Total Trades, Win Rate %, Loss Rate %, Break-Even Rate %.
  - Total Gross Profit, Total Gross Loss, Net Profit.
  - Profit Factor (`Gross Profit / abs(Gross Loss)`).
  - Expectancy (`(Win Rate * Avg Win) - (Loss Rate * Avg Loss)`).
  - Average Win, Average Loss, Win/Loss Ratio.
  - Maximum Drawdown ($ and % from peak balance/equity).
  - Consecutive Wins, Consecutive Losses.
  - Return on Investment (ROI) and Account Growth %.
- **FR-028 (Must):** Breakdown analytics: Performance by Day of Week, Hour of Day, Trading Session, Symbol, Direction, and Strategy.
- **FR-029 (Must):** Cumulative P&L curve and equity curve visual series.
- **FR-030 (Must):** Strictly non-hallucinated math: Zero LLM involvement in calculating financial statistics.

### 4.7 Prop Firm Risk Manager
- **FR-031 (Must):** Configurable prop firm challenge profiles (e.g., FTMO, FundingPips, 5%ers, Custom).
- **FR-032 (Must):** Real-time tracking of:
  - Daily Drawdown Limit (% and $ remaining).
  - Maximum Total Drawdown Limit (% and $ remaining).
  - Trailing Drawdown vs Static Drawdown toggle.
  - Profit Target progress bar.
- **FR-033 (Must):** Support for Balance-based vs Equity-based daily drawdown calculations.
- **FR-034 (Must):** Visual risk gauges and proactive warning banners when risk thresholds exceed 80% of limit.

### 4.8 Trading Behavior Analyzer
- **FR-035 (Must):** Evidence-based behavioral pattern detection:
  - **Revenge Trading:** Re-entering within < 15 minutes of a loss with equal or increased lot size.
  - **Overtrading:** Exceeding user-defined maximum daily trade count.
  - **Risk Escalation (Martingale tendency):** Increasing position size following consecutive losses.
  - **Session Drift:** Executing trades outside predefined active sessions.
  - **Premature Exit:** Cutting winning trades well before Take Profit while letting losers hit full Stop Loss.
- **FR-036 (Must):** Neutral, objective language. The analyzer states statistical facts and behavioral patterns without diagnosing medical or mental health conditions.

### 4.9 AI Strategy Performance Analyzer
- **FR-037 (Must):** Strategy tagging and performance breakdown across standard methodologies:
  - ICT (Inner Circle Trader)
  - Smart Money Concepts (SMC)
  - Classical Price Action (Support/Resistance, Breakout)
  - Custom user strategies
- **FR-038 (Must):** Benchmark setup profitability (e.g., "Silver Bullet" vs "London Open Judas Swing").

### 4.10 AI Chart Screenshot Analyzer (Vision)
- **FR-039 (Should):** Image upload support (PNG, JPG, WebP) for trading charts.
- **FR-040 (Should):** Structured visual feature breakdown for ICT/SMC concepts:
  - Liquidity Pools / Sweeps (BSL/SSL)
  - Market Structure Shift (MSS) / Break of Structure (BOS)
  - Fair Value Gap (FVG) / Imbalance detection
  - Order Block (OB) identification
  - Invalidation Level and Target
- **FR-041 (Must):** Strict uncertainty guardrail: AI must explicitly delineate what is directly visible in the image vs what is speculative interpretation.

### 4.11 Personal Trading Knowledge Base (RAG)
- **FR-042 (Must):** Secure file upload for user documents (PDF, Markdown, TXT) representing personal trading rules, playbooks, and checklists.
- **FR-043 (Must):** Text chunking, embedding generation, and vector indexing using PostgreSQL `pgvector`.
- **FR-044 (Must):** Tenant-isolated semantic retrieval: Users can only query their own uploaded documents.
- **FR-045 (Must):** Protection against prompt injection from uploaded files.

### 4.12 AI Trade Reviewer (Pre & Post-Trade)
- **FR-046 (Must):** Pre-Trade Review: Evaluates user's planned trade against personal rules, risk limits, and current account drawdown status.
- **FR-047 (Must):** Post-Trade Review: Generates an automated retrospective analyzing whether execution adhered to the declared strategy and risk rules.
- **FR-048 (Must):** Structured output schema with mandatory visual classification badges:
  - `[VERIFIED DATA]`
  - `[CALCULATED METRICS]`
  - `[HISTORICAL STATISTICS]`
  - `[AI INTERPRETATION]`

### 4.13 Beginner Learning Hub & Educational Resource Discovery
- **FR-049 (Should):** Interactive, structured educational curriculum from Beginner to Advanced:
  - Foundations: Forex terms, pips, lots, leverage, margin, sessions.
  - Risk Management: Sizing formulas, drawdown, R:R.
  - Price Action & Market Structure: Swings, trends, support/resistance.
  - SMC & ICT Concepts: Order blocks, liquidity, FVG, displacement.
  - Psychology & Journaling: Discipline, cognitive biases, post-trade reviews.
- **FR-050 (Should):** Curated directory of educational resources (educators, books, documentation, verified courses) with filter by topic, experience level, language, and cost (free vs paid).
- **FR-051 (Must):** Neutrality rule: No educator or platform shall be labeled "objectively the best." No affiliate links or unverified profitability claims.

---

## 5. Non-Functional Requirements (NFR)

### 5.1 Performance & Latency
- **NFR-001:** Deterministic financial analytics must calculate and render in < 250ms for portfolios up to 10,000 trades.
- **NFR-002:** MT5 incremental sync cycle execution time must complete within < 3 seconds under normal network conditions.
- **NFR-003:** AI streaming responses must initiate token streaming within < 1.5 seconds.
- **NFR-004:** Next.js frontend Core Web Vitals: LCP < 1.8s, FID/INP < 100ms, CLS < 0.05.

### 5.2 Security & Data Privacy
- **NFR-005:** All passwords hashed with bcrypt (minimum cost factor 12).
- **NFR-006:** All MT5 investor/account credentials stored encrypted at rest using AES-256-GCM.
- **NFR-007:** Account credentials and passwords must NEVER be passed to an LLM prompt or output in logs.
- **NFR-008:** Row-Level Security (RLS) or explicit tenant query filtering enforced across all database tables.
- **NFR-009:** API rate limiting on authentication and AI endpoints (e.g., 5 requests/minute for login, 30 requests/minute for AI analysis).

### 5.3 Reliability & Fault Tolerance
- **NFR-010:** System must continue functioning with 100% feature capability via CSV/manual entry if MT5 terminal connection is unavailable.
- **NFR-011:** Idempotent database operations: Ingesting the same MT5 report or CSV twice must never create duplicate records.
- **NFR-012:** Graceful degradation when external LLM APIs experience downtime (analytics and journal remain 100% operational).

### 5.4 Usability & Accessibility
- **NFR-013:** WCAG 2.1 AA compliance for color contrast, keyboard navigation, and screen-reader semantics.
- **NFR-014:** Support for standard `prefers-reduced-motion` to disable non-essential animations.
- **NFR-015:** Fully responsive design supporting desktop (1920x1080, 1440x900) and tablet/laptop (1024x768). Mobile view provides read-only journal and dashboard review.

---

## 6. MoSCoW Prioritization

| Priority | Module / Feature | Justification |
| :--- | :--- | :--- |
| **Must Have (MVP)** | JWT Auth & Multi-tenant User Isolation | Foundational security and tenant separation. |
| **Must Have (MVP)** | Trading Account Management (Multi-account) | Required for organizing trades. |
| **Must Have (MVP)** | MT5 Windows Terminal Prototype (Read-Only) | Core differentiator and user requirement. |
| **Must Have (MVP)** | Automatic MT5 Trade & Deal Sync | Automates the journaling friction. |
| **Must Have (MVP)** | CSV Import & Manual Trade Fallback | Guarantees usability if MT5 terminal is absent. |
| **Must Have (MVP)** | Aggregated Trading Journal & Filtering | Primary workspace for retail traders. |
| **Must Have (MVP)** | Deterministic Analytics Engine (NumPy/Pandas)| Zero-hallucination mathematical foundation. |
| **Must Have (MVP)** | Prop Firm Risk Manager (Drawdown Tracking) | Critical utility for funded account traders. |
| **Must Have (MVP)** | Rule-based Trading Behavior Analyzer | Identifies revenge trading and overtrading. |
| **Must Have (MVP)** | Strategy Performance Breakdown | Measures system efficacy (ICT/SMC/Price Action). |
| **Must Have (MVP)** | Document RAG Knowledge Base (pgvector) | Contextualizes AI advice with trader's playbook. |
| **Must Have (MVP)** | AI Pre/Post Trade Reviewer with Badges | Provides actionable feedback with safety tags. |
| **Must Have (MVP)** | Premium FinTech UI/UX (Next.js + Tailwind) | Professional SaaS standard for FYP excellence. |
| **Should Have** | AI Chart Screenshot Analyzer (Vision) | High visual appeal and utility for technical setups. |
| **Should Have** | Beginner Learning Hub | Educational value for university project scope. |
| **Should Have** | Educational Resource Discovery | Helps users find verified learning materials. |
| **Should Have** | Historical Setup Outcome Estimator (MAE/MFE) | Deeper quantitative edge analysis. |
| **Could Have** | ML Market Regime Classification | Advanced quantitative feature; depends on clean data. |
| **Could Have** | Optional n8n External Alerts (Telegram/Discord)| Notification workflow without polluting core backend. |
| **Won't Have (Out)** | Automated Live Trading Execution | Direct violation of safety principles and project scope. |
| **Won't Have (Out)** | Guaranteed "Buy/Sell" Signal Generation | Ethically and technically irresponsible. |
| **Won't Have (Out)** | High-frequency Tick-by-Tick Ingestion | Unnecessary architectural overhead for a journal/coach. |

---

## 7. Business Model & Cost Analysis

### 7.1 FYP vs Commercial Deployment
- **FYP Context:** 100% self-hosted or free-tier cloud infrastructure. Zero mandatory paid subscriptions.
- **Commercial SaaS Roadmap:**
  - **Free Tier:** 1 Account, CSV & Manual Entry, Core Analytics, Standard Journal, Community Learning Hub.
  - **Pro Tier ($19/month):** Unlimited Accounts, Real-time MT5 Live/Demo Sync, AI Trade Reviewer (50 queries/mo), Prop Firm Risk Engine, Screenshot Analyzer (20/mo).
  - **Elite Tier ($39/month):** Unlimited AI Reviewer, Unlimited Screenshots, Custom RAG Playbooks, Telegram/Discord Risk Alerts, Priority Processing.

### 7.2 Operational Cost Strategy (Low-Cost / Free-Tier)
- **FastAPI Backend & Next.js:** Self-hosted or hosted on free tiers (Vercel for frontend, Railway/Render free tier or local Windows server for backend).
- **Database:** Local PostgreSQL with pgvector (Zero cost) or Supabase/Neon free tier.
- **LLM / Vision:** Google Gemini 1.5/2.0 Flash (Free API tier / extremely low cost per 1M tokens) or local Ollama models (Llama 3 / Mistral) for 100% offline free execution.
- **MT5 Terminal:** Official desktop client (Free).
- **Automation:** Native Python asynchronous background workers (Celery/APScheduler) avoiding any paid n8n cloud instances.

---

## 8. Success Metrics & Key Performance Indicators (KPIs)

1. **Synchronization Reliability:** > 99.5% successful deal ingestion rate without duplicate entries.
2. **Deterministic Calculation Accuracy:** 100% mathematical parity with official MT5 terminal closed reports.
3. **AI Safety Compliance:** 0 instances of financial hallucination in calculated cards; 100% adherence to classification badge formatting.
4. **Behavioral Impact:** Measurable reduction in revenge-trading violations for active journalers over a 30-day period.
5. **System Performance:** Dashboard load time under 1.2 seconds with 5,000+ trade history.
