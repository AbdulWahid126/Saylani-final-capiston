# UI/UX Design System & Interface Specifications

## Project Title
**AI Trading Copilot — Intelligent Trading Analytics, Risk Management & Decision Support System**

---

## 1. Design Philosophy & Aesthetic Identity

### 1.1 Aesthetic Tone
The AI Trading Copilot interface is crafted as an elite, high-density **FinTech SaaS platform** inspired by the precision of **Linear**, the tactical depth of **TradingView**, and the institutional clarity of **Stripe & Bloomberg Terminal**.

- **Professional & Data-Centric:** Maximum signal-to-noise ratio. Information density without visual clutter.
- **Dark-Mode First:** Engineered for long trading sessions with minimal eye fatigue.
- **Zero Gimmicks:** Strict avoidance of tacky neon gradients, excessive blur, cartoonish 3D, and giant bloated cards.
- **Tactile Micro-Interactions:** Subtle, fluid feedback on hover, active states, and modal transitions using Framer Motion.
- **Information Clarity & Trust:** Color is functional, not decorative. Green is profit, red is loss, cyan is calculation, and purple is AI synthesis.

---

## 2. Design System Tokens

### 2.1 Color Palette (Tailwind HSL Semantic Variables)

```css
:root {
  /* Canvas & Neutral Hierarchy */
  --background: 222 47% 6%;          /* #080B11 Deep Obsidian Slate */
  --surface: 222 40% 9%;             /* #0E131F Card & Table Surface */
  --surface-hover: 222 35% 13%;       /* #151D2F Hover Row Surface */
  --surface-raised: 222 30% 16%;      /* #1D263B Modal / Popover */
  --border: 222 25% 18%;              /* #222C42 Subtle Hairline Border */
  --border-active: 222 40% 30%;       /* #2E3E61 Active Border */
  
  /* Typography Colors */
  --text-primary: 210 40% 98%;        /* #F8FAFC Bright Crisp White */
  --text-secondary: 215 20% 70%;      /* #94A3B8 Muted Information */
  --text-tertiary: 215 15% 45%;       /* #64748B Inactive / Placeholders */

  /* Functional Financial Semantics */
  --profit: 152 76% 45%;              /* #1BC773 Institutional Emerald */
  --profit-subtle: 152 76% 12%;       /* Profit background badge */
  --loss: 350 89% 60%;                /* #F43F5E Precision Crimson/Rose */
  --loss-subtle: 350 89% 14%;         /* Loss background badge */
  --warning: 38 92% 50%;              /* #F59E0B Warning / Breach Amber */
  --neutral-blue: 217 91% 60%;        /* #3B82F6 Information / Ticker Blue */

  /* Data Distinction Badges */
  --badge-verified: 152 76% 45%;      /* [VERIFIED DATA] */
  --badge-calc: 187 92% 52%;          /* [CALCULATED METRICS] */
  --badge-hist: 217 91% 60%;          /* [HISTORICAL STATISTICS] */
  --badge-ml: 38 92% 50%;             /* [ML ESTIMATES] */
  --badge-ai: 271 91% 65%;            /* [AI INTERPRETATION] */
}
```

### 2.2 Typography
- **Primary Interface Font:** `Inter` or `Geist Sans` (high legibility at small sizes: 11px–14px).
- **Financial Monospace Font:** `JetBrains Mono` or `Geist Mono` (tabular numbers for P&L, lot sizes, tick prices, timestamps, and order tickets).
- **Heading Scale:**
  - `h1`: 24px (1.5rem), SemiBold, tracking -0.02em.
  - `h2`: 18px (1.125rem), Medium, tracking -0.01em.
  - `h3`: 14px (0.875rem), SemiBold.
  - `body`: 13px (0.8125rem), Regular.
  - `caption / table`: 11px (0.6875rem), Medium, Monospace.

### 2.3 Elevation & Borders
- **Borders:** Crisp 1px solid hairline borders (`border-border/60`).
- **Shadows:** Highly restrained soft dark ambient shadows (`shadow-sm`, `shadow-md` with `rgba(0, 0, 0, 0.45)`).
- **Border Radius:** Consistent `rounded-lg` (8px) for cards, `rounded-md` (6px) for buttons/inputs, `rounded-full` for status pills.

---

## 3. UI/UX Component Ecosystem Evaluation

| Library / Tool | Recommendation | Evaluation & Rationale |
| :--- | :--- | :--- |
| **shadcn/ui & Radix UI** | **Core Foundation** | Unstyled accessible primitives (Dialog, Dropdown, Tabs, Tooltip, Popover). Fully owned source code, lightweight, zero vendor lock-in. |
| **Lucide Icons** | **Core Standard** | Lightweight, clean stroke consistency across trading icons (TrendingUp, AlertTriangle, ShieldCheck, Cpu, Terminal). |
| **Recharts** | **Core Analytics Charts** | Highly declarative React charting for Equity Curves, Drawdown waterfalls, and Win/Loss bar distributions. |
| **Lightweight Charts (TradingView)** | **Core Chart Renderer** | The gold standard for financial candlestick and price action charts. Fast canvas-based rendering with zero bloat. |
| **Framer Motion** | **Selective Use** | Used exclusively for tab transitions, modal entrances, and drawer slides (`layoutId`, simple opacity/scale fades). |
| **Magic UI & Aceternity UI** | **Selective Inspection** | Used only for 1–2 subtle landing page accents (e.g., Animated Grid Background or subtle border glow). Prohibited inside the dashboard to preserve performance and clean aesthetics. |
| **GSAP & Lenis** | **Avoid in Dashboard** | Lenis smooth scroll and GSAP heavy timelines interfere with standard browser scrolling, data tables, and accessibility. Reserved solely for landing page marketing scroll if required. |

---

## 4. Visual Classification Badges Specification

Every analytical card, AI review, and data table must incorporate the mandatory visual classification badge:

| Badge | Color (HSL) | Background | Description / Scope |
| :--- | :--- | :--- | :--- |
| `[VERIFIED DATA]` | Emerald (`#1BC773`) | `rgba(27, 199, 115, 0.12)` | Direct facts pulled from MT5 or broker ticket (deal time, volume, open/close price). |
| `[CALCULATED METRICS]` | Cyan (`#06B6D4`) | `rgba(6, 182, 212, 0.12)` | Deterministic backend math (Win Rate, Profit Factor, Net P&L, Drawdown). |
| `[HISTORICAL STATISTICS]` | Blue (`#3B82F6`) | `rgba(59, 130, 246, 0.12)` | Sample aggregations from past journaled setups ($N \ge 15$). |
| `[ML ESTIMATES]` | Amber (`#F59E0B`) | `rgba(245, 158, 11, 0.12)` | Machine learning regime classifiers, clustering, or MAE/MFE probability estimates. |
| `[AI INTERPRETATION]` | Purple (`#A855F7`) | `rgba(168, 85, 247, 0.12)` | Qualitative LLM commentary, playbook comparison, or psychological insights. |

---

## 5. Screen-by-Screen Layout Specifications

### 5.1 Main Executive Dashboard
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  [Logo] AI Trading Copilot   [Account Switcher: FTMO $100k (Live Sync)]  [Sync Now 🟢] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  KPI CARDS ROW                                                                         │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌─────────────────────────────┐  │
│  │ Net Realized  │ │ Win Rate      │ │ Profit Factor │ │ Daily Drawdown Remaining    │  │
│  │ +$3,420.50    │ │ 64.2% (27/42) │ │ 2.14          │ │ $1,850.00 / $5,000 (37%)    │  │
│  │ [CALCULATED]  │ │ [CALCULATED]  │ │ [CALCULATED]  │ │ [VERIFIED] [RISK GAUGE 🟢]  │  │
│  └───────────────┘ └───────────────┘ └───────────────┘ └─────────────────────────────┘  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  MAIN INTERACTIVE SECTION                                                              │
│  ┌──────────────────────────────────────────────────┐ ┌──────────────────────────────┐ │
│  │ CUMULATIVE EQUITY & BALANCE CURVE                │ │ BEHAVIOR & RISK RADAR        │ │
│  │ (Interactive Recharts / Lightweight Charts)      │ │ • Revenge Trading: 0 detected│ │
│  │                                                  │ │ • Overtrading: 2/5 trades max│ │
│  │                                                  │ │ • Session Drift: 1 trade (NY)│ │
│  │                                                  │ │ [CALCULATED] [BEHAVIOR ENGINE]│ │
│  └──────────────────────────────────────────────────┘ └──────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  RECENT TRADES & AI RETROSPECTIVES (Table with Instant Drawer View)                    │
│  Ticket  | Time    | Symbol | Type | Lots | P&L ($)  | Strategy    | Risk | AI Review│
│  #982141 | 14:32:10| EURUSD | BUY  | 2.00 | +$640.00 | ICT Silver B| 1.0% | Validated│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 MT5 Connection Wizard & Account Manager
- **Step 1: Account Type Selection:** Toggle between Live, Demo, Prop Firm Challenge, or Prop Firm Funded.
- **Step 2: Terminal IPC Connection Form:**
  - Broker Server (e.g., `FTMO-Server2`, `ICMarkets-Live01`).
  - Account Login Number (e.g., `21094821`).
  - Read-Only / Investor Password (with security tooltip explaining that Master password is not needed).
  - Terminal Path (defaults to auto-detected `C:\Program Files\MetaTrader 5\terminal64.exe`).
- **Step 3: Real-Time Handshake & Diagnostics:**
  - Status indicator (Connecting -> Handshake Confirmed -> Backfilling History -> Complete).
  - Progress bar showing deals ingested, positions aggregated, and initial balance snapshot.
- **Alternative Tab: CSV / Manual Ingestion:** Drag-and-drop zone for MT5 HTML/CSV reports with column auto-mapper.

### 5.3 Trading Journal & Trade Detail Drawer
- **Journal Table:**
  - Sticky header, high-density rows (36px row height).
  - Filter Bar: Date Range picker, Symbol dropdown, Direction, Outcome (Win, Loss, BE), Strategy, Session.
  - Columns: Ticket, Symbol, Direction, Lots, Entry Price, Exit Price, Duration, Gross Profit, Commission, Swap, Net P&L, Strategy, Setup, Actions.
- **Trade Detail Drawer (Opens on Row Click):**
  - Left Column: Deal breakdown (entry deal, partial close deals, final exit deal with tickets).
  - Middle Column: Interactive candlestick chart snippet showing entry, SL, TP, and exit points.
  - Right Column: User notes, uploaded chart screenshots, and the **AI Retrospective Card** (`[AI INTERPRETATION]`) evaluating setup execution against the user's playbook.

### 5.4 Prop Firm Risk Manager Screen
- **Visual Gauges:**
  - Circular or radial gauge for **Daily Loss Limit** (resets at broker midnight).
  - Horizontal progress bar for **Maximum Trailing / Static Drawdown**.
  - Target milestone bar for **Profit Target** ($8,000 / $10,000 for Phase 1).
- **Breach Warning Thresholds:**
  - Green (Normal): 0% – 50% of limit consumed.
  - Amber (Warning): 50% – 80% of limit consumed (Triggers banner notification).
  - Red (Danger): > 80% of limit consumed (Triggers urgent lock recommendation).
- **Rule Configuration Card:** Configure starting balance, daily reset timezone (e.g., UTC+2/broker server time), balance vs equity basis, and trailing stop calculation method.

### 5.5 AI Chart Screenshot Analyzer Screen
- **Upload Zone:** Drag and drop chart screenshot with instant thumbnail preview.
- **Strategy Selector:** Choose intended methodology (e.g., "ICT 2022 Model", "London Open Judas Swing", "Support/Resistance Breakout").
- **Structural Analysis Card:**
  - **Liquidity Check:** Identifies sweep of Buy-Side Liquidity (BSL) or Sell-Side Liquidity (SSL).
  - **Market Structure Shift (MSS):** Detects displacement candle and break of swing point.
  - **Fair Value Gap (FVG):** Highlights visible imbalance zone.
  - **Optimal Trade Entry (OTE):** Evaluates fibonacci retracement alignment.
  - **Uncertainty Disclosure:** Explicit declaration of image limitations and missing higher-timeframe context.

### 5.6 Personal Trading Knowledge Base (Playbooks)
- **Document Management:** Upload and manage personal PDF trading plans, rule checklists, and setup guidelines.
- **Chunk Inspector:** View how the system parses and indexes document chunks.
- **Semantic Test Query:** Search the knowledge base directly to verify how the AI retrieves personal rules.

### 5.7 Beginner Learning Hub & Resource Discovery
- **Curriculum Tree:** Visual roadmap from Level 1 (Forex Fundamentals) to Level 5 (Advanced ICT/SMC & Psychology).
- **Lesson Viewer:** Clean markdown reader with interactive diagrams, terminology glossaries, and knowledge checks.
- **Vetted Directory:** Searchable table of external books, educational YouTube channels, and courses with tags (Free/Paid, Level, Strategy Focus), complete with impartial descriptions.

---

## 6. Accessibility & Responsive States

- **Keyboard Navigation:** Full focus-trap in modals, `Tab` and `Shift+Tab` cycling, `Esc` to dismiss drawers.
- **Screen Reader Semantics:** `aria-label`, `aria-describedby`, and `role="status"` on live updating sync widgets.
- **Reduced Motion:** If `prefers-reduced-motion` is enabled, all Framer Motion transforms and fade transitions are replaced with immediate visibility toggles.
- **Empty States:** Every table and view includes a dedicated illustrated empty state with actionable buttons (e.g., "No trades found. Connect MT5 or Import CSV").
- **Error States:** Granular error callouts with error codes and recovery actions (e.g., "Terminal connection timeout — verify that terminal64.exe is running").
