"""Curriculum content and curated educational resource catalog.

Provides structured, neutral, beginner-friendly trading education covering:
- Forex Fundamentals
- Risk Management & Position Sizing
- Technical Analysis & Price Action
- Smart Money Concepts (SMC)
- Inner Circle Trader (ICT) Concepts
- Trading Psychology & Behavioral Discipline

Strictly adheres to:
- Zero guaranteed profit claims.
- Distinction between market mechanics and discretionary frameworks.
- Neutral, verified educational references with no referral links.
- Deterministic mathematical calculations for hypothetical examples.
"""

from app.schemas.learning import (
    CostClassification,
    CuratedResourceResponse,
    CurriculumCategoryResponse,
    CurriculumLessonDetail,
    DifficultyLevel,
    HypotheticalExample,
    KeyTermItem,
    ResourceType,
)

CURRICULUM_CATEGORIES: list[CurriculumCategoryResponse] = [
    CurriculumCategoryResponse(
        id="forex-fundamentals",
        title="Forex Fundamentals & Market Mechanics",
        short_description="Essential foundations of foreign exchange: currency pairs, pips, spreads, leverage, and sessions.",
        icon="Coins",
        lesson_count=3,
        order=1,
    ),
    CurriculumCategoryResponse(
        id="risk-management",
        title="Risk Management & Capital Preservation",
        short_description="Mathematical risk control, deterministic position sizing, stop-loss strategy, and drawdown survival.",
        icon="ShieldCheck",
        lesson_count=3,
        order=2,
    ),
    CurriculumCategoryResponse(
        id="technical-analysis",
        title="Technical Analysis & Price Action Foundations",
        short_description="Support, resistance, market trends, swing points, and candlestick anatomy in structural context.",
        icon="TrendingUp",
        lesson_count=2,
        order=3,
    ),
    CurriculumCategoryResponse(
        id="smc",
        title="Smart Money Concepts (SMC) Framework",
        short_description="Discretionary market structure, Break of Structure (BOS), Change of Character (CHoCH), Order Blocks, and Liquidity.",
        icon="Layers",
        lesson_count=2,
        order=4,
    ),
    CurriculumCategoryResponse(
        id="ict",
        title="Inner Circle Trader (ICT) Framework",
        short_description="Session kill zones, Optimal Trade Entry (OTE), Fair Value Gaps (FVG), and liquidity sweeps analyzed objectively.",
        icon="Compass",
        lesson_count=2,
        order=5,
    ),
    CurriculumCategoryResponse(
        id="psychology",
        title="Trading Psychology & Behavioral Discipline",
        short_description="Mitigating FOMO, eliminating revenge trading, cognitive biases, and systematic journaling habits.",
        icon="Brain",
        lesson_count=2,
        order=6,
    ),
]

CURRICULUM_LESSONS: list[CurriculumLessonDetail] = [
    # -------------------------------------------------------------------------
    # 1. Forex Fundamentals
    # -------------------------------------------------------------------------
    CurriculumLessonDetail(
        id="fx-pairs-pips-spreads",
        slug="currency-pairs-pips-spreads",
        title="Currency Pairs, Pips & Spreads Explained",
        category_id="forex-fundamentals",
        category_title="Forex Fundamentals & Market Mechanics",
        short_description="Learn how currencies are quoted in pairs, calculate pip values accurately, and understand transaction costs via spreads.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=10,
        prerequisites=[],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Distinguish between base and quote currencies in any foreign exchange quote.",
            "Calculate pip values across 4-decimal currency pairs and Japanese Yen (JPY) crosses.",
            "Explain bid-ask spread mechanics and compute transaction costs per trade.",
        ],
        key_terms=[
            KeyTermItem(
                term="Base Currency",
                definition="The first currency listed in a currency pair (e.g., EUR in EUR/USD). It represents the unit being bought or sold.",
            ),
            KeyTermItem(
                term="Quote Currency",
                definition="The second currency listed in a currency pair (e.g., USD in EUR/USD). It represents the price of one unit of the base currency.",
            ),
            KeyTermItem(
                term="Pip (Percentage in Point)",
                definition="The standardized unit of price movement, typically equal to 0.0001 for most currency pairs, and 0.01 for pairs involving the Japanese Yen (JPY).",
            ),
            KeyTermItem(
                term="Spread",
                definition="The difference between the Bid (selling) price and Ask (buying) price charged by brokers and market makers as transaction cost.",
            ),
        ],
        content_markdown="""### Understanding Currency Quotations

In the foreign exchange market, currencies are traded in standardized pairs. When you trade forex, you are simultaneously buying one currency while selling another.

Every pair is structured as:
$$\\text{Base Currency} \\; / \\; \\text{Quote Currency}$$

For example, in **EUR/USD = 1.0850**:
- **EUR** is the base currency.
- **USD** is the quote currency.
- The exchange rate means **1 Euro equals 1.0850 US Dollars**.

---

### What is a Pip and a Pipette?

A **pip** (Percentage in Point) is the standardized unit measuring price changes:
- For pairs quoted to 4 decimal places (e.g., EUR/USD, GBP/USD, AUD/USD), **1 pip = 0.0001**.
- For pairs quoted to 2 decimal places (e.g., USD/JPY, EUR/JPY), **1 pip = 0.01**.
- Many modern brokers provide fractional pips called **pipettes** (5th decimal place for standard pairs, 3rd decimal place for JPY pairs), where **10 pipettes = 1 pip**.

#### Standard Pip Value Formula
For pairs where USD is the quote currency (e.g., EUR/USD, GBP/USD):
- **1 Standard Lot (100,000 units):** $10.00 per pip
- **1 Mini Lot (10,000 units):** $1.00 per pip
- **1 Micro Lot (1,000 units):** $0.10 per pip

---

### The Spread: Understanding Execution Costs

Every currency pair has two prices displayed at all times:
1. **Bid Price:** The price at which the broker or market will buy from you (the price you sell at).
2. **Ask Price:** The price at which the broker or market will sell to you (the price you buy at).

The spread is calculated as:
$$\\text{Spread} = \\text{Ask Price} - \\text{Bid Price}$$

When you open a Buy trade, you execute at the Ask. Because you must exit at the Bid, the trade begins immediately at a slight deficit equivalent to the spread cost. Spread expands during low liquidity periods (such as market rollover at 17:00 EST) and high-impact macroeconomic news releases.
""",
        hypothetical_example=HypotheticalExample(
            title="Calculating Spread Cost on EUR/USD",
            scenario="A trader enters a Buy position of 1.0 standard lot on EUR/USD. The broker quotes Bid: 1.0848, Ask: 1.0850.",
            calculation="Spread = Ask (1.0850) - Bid (1.0848) = 0.0002 = 2.0 pips. On 1.0 standard lot (100,000 units), 1 pip = $10.00. Total spread cost = 2.0 pips * $10.00/pip = $20.00.",
            outcome="The position opens immediately with a floating P&L of -$20.00. The market must move 2.0 pips in the trader's favor just to reach the break-even threshold.",
            key_takeaway="Always account for the spread when placing stop-losses and profit targets, especially on lower timeframes where spread represents a larger percentage of your target.",
        ),
        common_mistakes=[
            "Ignoring spread expansion during the daily rollover period (21:00-22:00 GMT), leading to premature stop-out.",
            "Confusing pip value calculations on JPY currency pairs where 1 pip equals 0.01 instead of 0.0001.",
            "Failing to account for spread when setting limit orders, resulting in unfilled entries.",
        ],
        recap="Currencies trade in base/quote pairs. A pip is 0.0001 (or 0.01 for JPY pairs). The difference between the Bid and Ask price is the spread, representing an unavoidable cost of execution that must be factored into trade expectancy.",
    ),
    CurriculumLessonDetail(
        id="fx-leverage-margin-liquidation",
        slug="leverage-margin-liquidation",
        title="Leverage, Margin & Liquidation Mechanics",
        category_id="forex-fundamentals",
        category_title="Forex Fundamentals & Market Mechanics",
        short_description="Master the mathematics of financial leverage, margin requirements, margin calls, and account stop-out levels.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=12,
        prerequisites=["fx-pairs-pips-spreads"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Define leverage and used margin mathematically.",
            "Understand why leverage amplifies both potential profits and catastrophic losses equally.",
            "Calculate margin level percentage and recognize warning thresholds for margin calls and automatic stop-out.",
        ],
        key_terms=[
            KeyTermItem(
                term="Financial Leverage",
                definition="A ratio (such as 1:30 or 1:100) allowing a trader to control a large nominal contract size using a smaller deposit of capital.",
            ),
            KeyTermItem(
                term="Used Margin",
                definition="The collateral amount locked by the broker from your account balance to maintain an open leveraged position.",
            ),
            KeyTermItem(
                term="Margin Level (%)",
                definition="The ratio of Account Equity to Used Margin expressed as a percentage: (Equity / Used Margin) * 100.",
            ),
            KeyTermItem(
                term="Stop-Out / Liquidation",
                definition="The automatic closing of open positions by the broker when equity falls below a predetermined margin level threshold (e.g., 50%).",
            ),
        ],
        content_markdown="""### What is Financial Leverage?

Leverage allows market participants to trade notional position sizes significantly larger than their deposited capital. It is expressed as a ratio such as **1:30**, **1:100**, or **1:500**.

With **1:100 leverage**, a deposit of **$1,000** allows you to control a position with a notional value of **$100,000** (one standard lot).

$$\\text{Required Margin} = \\frac{\\text{Contract Size} \\times \\text{Asset Price}}{\\text{Leverage Ratio}}$$

---

### The Two-Edged Sword: Why Leverage Kills Accounts

While leverage is often marketed as a way to generate outsized returns with small deposits, mathematical symmetry dictates that leverage magnifies losses at the exact same rate.

Consider an account with **$1,000 balance**:
- **Trader A (Unleveraged / Conservative):** Opens 0.05 lots ($5,000 notional). A 100-pip move against the position produces a **-$50 loss** (5% drawdown). The account remains fully operational.
- **Trader B (Heavily Leveraged):** Opens 1.00 lot ($100,000 notional). A 100-pip move against the position produces a **-$1,000 loss** (100% loss). The account is completely wiped out.

---

### Margin Call vs. Stop-Out Level

To protect the brokerage from negative customer balances, brokers monitor your **Margin Level (%)**:

$$\\text{Margin Level} = \\left( \\frac{\\text{Account Equity}}{\\text{Used Margin}} \\right) \\times 100\\%$$

- **Margin Call (typically 100%):** The broker sends a notification that equity has dropped to equal used margin. You cannot open new trades unless you deposit funds or close positions.
- **Stop-Out / Liquidation Level (typically 50% or 20%):** If losses continue and equity drops below the broker's stop-out threshold, the broker's automated risk engine immediately forces-closes your worst-performing positions at market price.
""",
        hypothetical_example=HypotheticalExample(
            title="Hypothetical Margin Call and Stop-Out Scenario",
            scenario="A trader deposits $2,000 in a retail account offering 1:100 leverage. They open 1.8 standard lots of EUR/USD ($180,000 notional). Required margin is $1,800, leaving $200 in free margin. Broker stop-out level is 50%.",
            calculation="At 1.8 lots, EUR/USD pip value is $18.00/pip. If price moves 10 pips against the trade, floating loss is -$180. Equity drops to $2,000 - $180 = $1,820 (Margin Level = 101%). If price moves an additional 60 pips against the trade (total -70 pips = -$1,260), equity falls to $740. Margin level drops to ($740 / $1,800) * 100 = 41.1%, breaching the 50% stop-out threshold.",
            outcome="The broker immediately initiates automated liquidation, executing a market close. The trader loses $1,260 plus slippage within minutes.",
            key_takeaway="Excessive leverage transforms routine market fluctuations into existential account threats. Institutional traders routinely risk only 0.5% to 1.0% of capital per trade, maintaining margin levels well above 1,000%.",
        ),
        common_mistakes=[
            "Viewing high available broker leverage (e.g., 1:500) as an incentive to trade maximum lot sizes rather than as an operational tool.",
            "Entering trades without calculating the margin requirement and remaining free margin cushion.",
            "Adding more contracts to a losing position near margin call in hopes of an immediate rebound.",
        ],
        recap="Leverage is borrowed buying power that requires collateral (used margin). When equity drops below broker thresholds, stop-out liquidation occurs automatically. Protecting margin requires disciplined position sizing.",
    ),
    CurriculumLessonDetail(
        id="fx-market-sessions-order-types",
        slug="market-sessions-order-types",
        title="Market Sessions, Order Types & Basic Candlesticks",
        category_id="forex-fundamentals",
        category_title="Forex Fundamentals & Market Mechanics",
        short_description="Explore global trading session liquidity cycles, essential pending order mechanics, and candlestick anatomy.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=14,
        prerequisites=["fx-pairs-pips-spreads"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Identify the three major global trading sessions (Asian, London, New York) and their volatility profiles.",
            "Distinguish between Market orders, Limit orders, and Stop orders.",
            "Read candlestick components: Open, High, Low, Close (OHLC), real body, and shadows/wicks.",
        ],
        key_terms=[
            KeyTermItem(
                term="London-New York Overlap",
                definition="The 4-hour window (approx. 13:00 to 17:00 GMT / 08:00 to 12:00 EST) when both London and New York centers are active, driving the highest volume and liquidity in the global forex market.",
            ),
            KeyTermItem(
                term="Market Order",
                definition="An instruction to execute immediately at the best available current market price.",
            ),
            KeyTermItem(
                term="Limit Order",
                definition="A pending order to buy below the current market price (Buy Limit) or sell above the current market price (Sell Limit).",
            ),
            KeyTermItem(
                term="Stop Order",
                definition="A pending order to buy above current market price (Buy Stop) or sell below current market price (Sell Stop) once price reaches a trigger level.",
            ),
        ],
        content_markdown="""### The 24-Hour Global Market Cycle

The forex market operates 24 hours a day, 5 days a week, following the sun across global financial centers:

1. **Asian Session (Tokyo / Sydney):** 00:00 - 09:00 GMT. Characterized by lower volatility and consolidation on EUR/USD, with primary volume concentrated in JPY and AUD pairs.
2. **London Session:** 07:00 - 16:00 GMT. The largest financial center for foreign exchange, generating major trend expansions.
3. **New York Session:** 12:00 - 21:00 GMT. Second largest center; driven by US macroeconomic data releases (CPI, NFP, FOMC).
4. **London-New York Overlap (13:00 - 17:00 GMT):** Peak market liquidity, tightest spreads, and significant institutional participation.

---

### Pending Orders vs. Market Orders

Choosing the right execution order type is critical for slippage control:

- **Market Order:** Fills immediately at the next available quote. In fast markets or news events, market orders can experience significant negative slippage.
- **Buy Limit:** Places a purchase request **below** current price, expecting price to retrace down, test a level, and bounce upward.
- **Sell Limit:** Places a sell request **above** current price, expecting price to retrace up and reverse downward.
- **Buy Stop:** Places a buy request **above** current price, executing a momentum entry once a breakout level is breached.
- **Sell Stop:** Places a sell request **below** current price, executing a momentum entry once support breaks.

---

### Candlestick Anatomy

Every Japanese candlestick encapsulates price action over a specified timeframe (e.g., M15, H1, D1):
- **Open (O):** The initial trade price during the period.
- **High (H):** The highest recorded price during the period.
- **Low (L):** The lowest recorded price during the period.
- **Close (C):** The final trade price during the period.

The rectangular area between Open and Close is the **Real Body**. The thin vertical lines extending above and below are the **Wicks (or Shadows)**, indicating price rejection and liquidity discovery.
""",
        hypothetical_example=HypotheticalExample(
            title="Choosing Order Type During London Open",
            scenario="EUR/USD is trading at 1.0850 at 07:30 GMT. A trader identifies strong support at 1.0830 and a resistance breakout level at 1.0880.",
            calculation="Case A (Mean Reversion): Trader sets a Buy Limit at 1.0830 with Stop Loss at 1.0815.\nCase B (Breakout Momentum): Trader sets a Buy Stop at 1.0882 with Stop Loss at 1.0865.",
            outcome="If price pulls back smoothly to 1.0830 and touches it, Case A fills as a maker order without paying market chase premium. If price instead rallies violently through 1.0880, Case B activates automatically upon confirmation.",
            key_takeaway="Pre-defining your entry mechanism via pending orders protects you from emotional market-chasing during high-velocity session opens.",
        ),
        common_mistakes=[
            "Executing market orders directly into high-impact news releases, resulting in severe spread widening and negative slippage.",
            "Confusing Buy Limits with Buy Stops, causing an accidental instant fill at adverse prices.",
            "Trading during low-liquidity session lulls where wide spreads erode risk-to-reward ratios.",
        ],
        recap="Forex moves through three primary daily sessions with maximum liquidity during the London-NY overlap. Utilizing pending orders (Limits and Stops) ensures disciplined execution over emotional market chasing.",
    ),
    # -------------------------------------------------------------------------
    # 2. Risk Management
    # -------------------------------------------------------------------------
    CurriculumLessonDetail(
        id="risk-stop-loss-take-profit-rr",
        slug="stop-loss-take-profit-rr",
        title="Stop-Loss, Take-Profit & Risk-to-Reward Dynamics",
        category_id="risk-management",
        category_title="Risk Management & Capital Preservation",
        short_description="Understand why high win rates are unnecessary with positive mathematical expectancy and disciplined stop-loss placement.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=12,
        prerequisites=["fx-pairs-pips-spreads"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Formulate mathematical expectancy for a trading strategy.",
            "Calculate Risk-to-Reward Ratio (R:R) and required break-even win rate.",
            "Explain why every trade requires a non-negotiable stop-loss prior to execution.",
        ],
        key_terms=[
            KeyTermItem(
                term="Stop-Loss Order",
                definition="A predefined exit order that closes a trade at a set price to prevent catastrophic capital loss if the market invalidates the trade thesis.",
            ),
            KeyTermItem(
                term="Risk-to-Reward Ratio (R:R)",
                definition="The ratio between the amount risked on a trade (distance to stop loss) and the potential gain (distance to take profit).",
            ),
            KeyTermItem(
                term="Mathematical Expectancy",
                definition="The average monetary return or R-multiple expected per trade over a large sample of executions: (Win Rate * Avg Win) - (Loss Rate * Avg Loss).",
            ),
        ],
        content_markdown="""### The High Win-Rate Fallacy

A pervasive misconception among novice traders is that successful trading requires an 80% or 90% win rate. In reality, institutional proprietary trading desks and algorithmic funds frequently operate with win rates between **40% and 55%**, achieving profitability through **asymmetric risk-to-reward ratios**.

$$\\text{Break-Even Win Rate} = \\frac{1}{1 + \\text{Reward:Risk Ratio}} \\times 100\\%$$

- With a **1:1 R:R**, you must win **50.0%** of trades to break even.
- With a **1:2 R:R**, you must win only **33.3%** of trades to break even.
- With a **1:3 R:R**, you must win only **25.0%** of trades to break even.

Conversely, a trader with a 90% win rate who risks $10 to make $1 (inverted 10:1 risk) will surrender all accumulated gains in a single adverse trade.

---

### The Expectancy Equation

Mathematical expectancy determines whether a trading system is fundamentally viable:

$$\\mathbb{E} = (P_{\\text{win}} \\times W) - (P_{\\text{loss}} \\times L)$$

Where:
- $P_{\\text{win}}$ = Probability of winning trade
- $W$ = Average winning trade amount
- $P_{\\text{loss}}$ = Probability of losing trade ($1 - P_{\\text{win}}$)
- $L$ = Average losing trade amount

If $\\mathbb{E} > 0$, the strategy has positive mathematical expectancy over time, assuming disciplined execution without emotional interference.
""",
        hypothetical_example=HypotheticalExample(
            title="Comparing Two Hypothetical Traders Across 100 Trades",
            scenario="Trader Alpha achieves a 40% win rate with a strict 1:2.5 Risk-to-Reward ratio (risking $100 to gain $250). Trader Beta achieves an 85% win rate with an inverted 1:0.2 ratio (risking $500 to gain $100).",
            calculation="Trader Alpha: 40 wins * $250 = +$10,000. 60 losses * $100 = -$6,000. Net Profit = +$4,000.\nTrader Beta: 85 wins * $100 = +$8,500. 15 losses * $500 = -$7,500. Net Profit = +$1,000 (with high vulnerability to an extended losing streak).",
            outcome="Trader Alpha finishes with 4x the net capital gain of Trader Beta despite losing the majority (60%) of all executed trades.",
            key_takeaway="Focus on execution asymmetry rather than emotional attachment to being 'right' on individual trade outcomes.",
        ),
        common_mistakes=[
            "Moving stop losses further away during live trades as price approaches them, turning a calculated loss into account destruction.",
            "Taking profits prematurely at +0.5R while holding losing trades to -1.0R or worse, destroying strategy expectancy.",
            "Trading without any pre-defined stop loss, trusting manual discretionary intervention during high volatility.",
        ],
        recap="Positive expectancy does not require high win rates. A disciplined stop-loss and favorable risk-to-reward ratio mathematically protect long-term capital.",
    ),
    CurriculumLessonDetail(
        id="risk-deterministic-position-sizing",
        slug="deterministic-position-sizing",
        title="Deterministic Position Sizing Formula",
        category_id="risk-management",
        category_title="Risk Management & Capital Preservation",
        short_description="Learn the exact, non-negotiable mathematical formula to calculate lot size based on account equity and stop loss pips.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=15,
        prerequisites=["risk-stop-loss-take-profit-rr", "fx-leverage-margin-liquidation"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Calculate precise contract lot sizes using deterministic equity-risk formulas.",
            "Never risk more than a pre-defined percentage (e.g., 1.0%) on any single setup.",
            "Adjust position sizing dynamically when stop loss distance varies across different setups.",
        ],
        key_terms=[
            KeyTermItem(
                term="Fixed Fractional Risk",
                definition="A risk management method where a trader risks an identical percentage of current account equity (typically 0.5% to 2.0%) on every single trade.",
            ),
            KeyTermItem(
                term="Pip Value Factor",
                definition="The cash value of one pip of price movement for one standard lot of the given currency pair.",
            ),
        ],
        content_markdown="""### Why Fixed Lot Sizing is Mathematically Flawed

A common beginner error is trading arbitrary fixed lot sizes (e.g., always clicking "0.5 lots" or "1.0 lot") regardless of whether the stop loss is 10 pips or 80 pips away.

- A 1.0 lot trade with a **10-pip stop** risks **$100**.
- A 1.0 lot trade with an **80-pip stop** risks **$800**.

This creates unpredictable variance, where a single wide-stop loss wipes out the gains of multiple narrow-stop winners.

---

### The Deterministic Sizing Formula

To maintain strict risk consistency, lot size must be calculated dynamically for every single setup:

$$\\text{Dollar Risk Amount} = \\text{Account Balance} \\times \\left( \\frac{\\text{Risk \\%}}{100} \\right)$$

$$\\text{Position Size (Lots)} = \\frac{\\text{Dollar Risk Amount}}{\\text{Stop Loss Distance in Pips} \\times \\text{Pip Value per Standard Lot}}$$

For standard USD quote pairs (EUR/USD, GBP/USD, AUD/USD), the pip value for 1.0 standard lot is exactly **$10.00**.
""",
        hypothetical_example=HypotheticalExample(
            title="Calculating Lot Size for a $25,000 Prop Challenge Account",
            scenario="Account balance is $25,000. Risk policy allows 1.0% maximum risk per trade. Trader identifies a setup on GBP/USD with entry at 1.2850 and stop loss at 1.2825 (25 pips). Pip value is $10.00 per standard lot.",
            calculation="Step 1: Dollar Risk = $25,000 * 0.01 = $250.00.\nStep 2: Risk per standard lot = 25 pips * $10.00 = $250.00.\nStep 3: Lot Size = $250.00 / $250.00 = 1.00 standard lot.",
            outcome="If the setup is stopped out at 1.2825, the loss is exactly $250.00 (1.0% of balance), perfectly within the risk policy.",
            key_takeaway="Whenever the stop loss distance changes, the lot size must change inversely. If the stop loss was 50 pips, lot size would be 0.50 lots; if 12.5 pips, lot size would be 2.00 lots.",
        ),
        common_mistakes=[
            "Guessing lot size in the trading terminal under time pressure instead of executing the formula.",
            "Increasing lot size after a losing trade to quickly recoup losses (a major behavioral violation called lot swelling).",
            "Failing to account for currency conversion when trading pairs where USD is the base currency (e.g., USD/CAD or USD/CHF).",
        ],
        recap="Position sizing must always be derived mathematically from your stop-loss distance and dollar risk threshold. Never use arbitrary fixed lot sizes.",
    ),
    CurriculumLessonDetail(
        id="risk-drawdown-recovery-math",
        slug="drawdown-recovery-math",
        title="Drawdown Mechanics & Capital Asymmetry",
        category_id="risk-management",
        category_title="Risk Management & Capital Preservation",
        short_description="Understand peak-to-trough drawdowns and the non-linear mathematical difficulty of recovering from account losses.",
        difficulty=DifficultyLevel.INTERMEDIATE,
        estimated_minutes=12,
        prerequisites=["risk-deterministic-position-sizing"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Distinguish between Maximum Drawdown, Relative Drawdown, and Daily Drawdown limits.",
            "Understand the asymmetric mathematical recovery curve for capital losses.",
            "Implement defensive capital preservation rules during losing streaks.",
        ],
        key_terms=[
            KeyTermItem(
                term="Maximum Drawdown (MDD)",
                definition="The peak-to-trough decline during a specific record period of an investment, expressed as a percentage of the peak value.",
            ),
            KeyTermItem(
                term="Asymmetric Recovery",
                definition="The mathematical principle that losing capital reduces the base upon which future percentage gains are calculated, requiring exponentially larger returns to break even.",
            ),
        ],
        content_markdown="""### The Geometry of Capital Loss

When you lose money in a trading account, the percentage gain required to return to the original balance is always greater than the percentage lost:

$$\\text{Required Gain \\%} = \\left( \\frac{1}{1 - \\text{Loss Fraction}} - 1 \\right) \\times 100\\%$$

| Account Loss (%) | Required Gain to Break Even (%) |
|:----------------:|:-------------------------------:|
| 5%               | +5.3%                           |
| 10%              | +11.1%                          |
| 20%              | +25.0%                          |
| 30%              | +42.9%                          |
| 40%              | +66.7%                          |
| **50%**          | **+100.0%**                     |
| 75%              | +300.0%                         |
| **90%**          | **+900.0%**                     |

A 50% drawdown requires a 100% gain—effectively doubling your remaining funds—just to return to your starting capital. At a 90% loss, recovery is statistically improbable.

---

### Prop Firm Drawdown Frameworks

Modern institutional and proprietary trading firms enforce two critical boundaries:
1. **Daily Loss Limit (typically 4% to 5%):** Trailing or balance-based circuit breaker that halts trading for the calendar day if breached.
2. **Maximum Trailing Drawdown (typically 8% to 10%):** Absolute ceiling relative to starting capital or high-water mark that terminates the account if violated.
""",
        hypothetical_example=HypotheticalExample(
            title="The Trap of Escalating Risk in Drawdown",
            scenario="A trader loses 20% of a $10,000 account down to $8,000. Frustrated, they increase their risk per trade from 1% to 5% ($400) to 'make it back quickly'.",
            calculation="With 5% risk per trade on the smaller balance, a standard 4-trade losing streak incurs: 4 * $400 = -$1,600. Account balance drops to $6,400 (36% total drawdown). Required recovery gain rises from +25% to +56.25%.",
            outcome="The trader has placed the account in extreme jeopardy. Had they reduced risk to 0.5% ($40 per trade) during the losing streak, the 4-trade streak would have cost only $160 (1.6%), preserving capital.",
            key_takeaway="During a drawdown, the only mathematically sound action is to reduce risk or pause trading, never escalate risk.",
        ),
        common_mistakes=[
            "Doubling trade size during a drawdown (Martingale strategy), which mathematically guarantees eventual account wipeout.",
            "Ignoring daily drawdown limits set by prop firms and blowing accounts in a single chaotic session.",
            "Failing to track high-water equity marks, leading to surprise breaches of trailing drawdown rules.",
        ],
        recap="Capital loss is asymmetric: a 50% loss demands a 100% gain to recover. Surviving losing streaks requires defensive risk management and immediate risk reduction during drawdowns.",
    ),
    # -------------------------------------------------------------------------
    # 3. Technical Analysis
    # -------------------------------------------------------------------------
    CurriculumLessonDetail(
        id="ta-support-resistance-market-structure",
        slug="support-resistance-market-structure",
        title="Support, Resistance & Market Structure Foundations",
        category_id="technical-analysis",
        category_title="Technical Analysis & Price Action Foundations",
        short_description="Master horizontal inflection levels, role reversal, swing points, and multi-timeframe market structure.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=12,
        prerequisites=["fx-market-sessions-order-types"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Identify objective horizontal support and resistance zones based on historical price reactions.",
            "Explain the concept of role reversal (polarization of support and resistance).",
            "Map market structure using Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), and Lower Lows (LL).",
        ],
        key_terms=[
            KeyTermItem(
                term="Support Level",
                definition="A price zone where buying interest is historically strong enough to overcome selling pressure and halt or reverse a downward price trajectory.",
            ),
            KeyTermItem(
                term="Resistance Level",
                definition="A price zone where selling interest is historically strong enough to overcome buying pressure and halt or reverse an upward price trajectory.",
            ),
            KeyTermItem(
                term="Role Reversal (Polarity)",
                definition="The technical phenomenon where a broken support level transitions into future resistance, or broken resistance becomes future support.",
            ),
        ],
        content_markdown="""### Price Memory: Why Support and Resistance Exist

Support and resistance levels represent historical inflection zones where large institutional orders were executed. Price has memory because institutional participants evaluate risk relative to significant benchmark levels:

1. **Horizontal Zones vs. Single Lines:** Support and resistance should be conceptualized as **price bands or zones** rather than exact micro-pip lines, as order clusters span a price range.
2. **Freshness of Levels:** A level tested 1-2 times with strong rejection is generally considered fresh. However, repeated tests (4+ times) often weaken a level as resting limit orders are progressively absorbed by market participants.

---

### Polarity & Role Reversal

When a significant support level is definitively broken by strong momentum (a decisive candle close below the zone), market polarity flips:
- Buyers who bought at the support level are trapped at a loss.
- When price pulls back to the broken level, trapped buyers look to exit at break-even (selling), and breakout sellers add to positions.
- Consequently, **broken support becomes new resistance**.

---

### Foundational Market Structure

Price moves in cyclical expansions and retracements:
- **Uptrend (Bullish Structure):** Characterized by a sequence of **Higher Highs (HH)** and **Higher Lows (HL)**. As long as price respects the previous HL, the bullish structure remains intact.
- **Downtrend (Bearish Structure):** Characterized by a sequence of **Lower Highs (LH)** and **Lower Lows (LL)**.
- **Range / Consolidation:** Price oscillates between horizontal boundaries without establishing directional swing progression.
""",
        hypothetical_example=HypotheticalExample(
            title="Trading a Role Reversal on EUR/USD",
            scenario="EUR/USD has traded between 1.0800 support and 1.0900 resistance for three weeks. A high-momentum 4-hour candle closes definitively at 1.0770, breaking support.",
            calculation="Former support zone: 1.0795 - 1.0805. Trader waits for price to pull back toward the broken level rather than chasing the breakout at 1.0770. Price retraces to 1.0800, prints a bearish rejection pin bar on M15. Entry: 1.0795. Stop Loss: 1.0820 (25 pips). Target: 1.0745 (50 pips).",
            outcome="Trade achieves a 1:2 Risk-to-Reward ratio as former support acts as new resistance.",
            key_takeaway="Patience to wait for a retest of broken structure significantly improves risk-to-reward ratios compared to emotionally chasing breakouts.",
        ),
        common_mistakes=[
            "Cluttering charts with dozens of arbitrary horizontal lines drawn across every minor wick on M1.",
            "Assuming support and resistance lines are impassable walls rather than permeable liquidity zones.",
            "Trading against the higher timeframe market structure (e.g., buying a minor M5 bounce while H4 is in a steep downtrend).",
        ],
        recap="Support and resistance zones mark areas of order concentration. Broken levels invert roles through polarity. Aligning trades with higher-timeframe swing structure maximizes probability.",
    ),
    CurriculumLessonDetail(
        id="ta-candlestick-anatomy-price-action",
        slug="candlestick-anatomy-price-action",
        title="Candlestick Patterns & High-Probability Price Action",
        category_id="technical-analysis",
        category_title="Technical Analysis & Price Action Foundations",
        short_description="Learn how to read rejection wicks, engulfing bars, and inside bars strictly within key structural market context.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=10,
        prerequisites=["ta-support-resistance-market-structure"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Identify key price action signals: Rejection Pin Bars (Hammers/Shooting Stars), Engulfing Candles, and Inside Bars.",
            "Understand why candlestick patterns have zero statistical edge when traded in isolation without structural confluence.",
            "Evaluate candle body-to-wick proportions to assess buyer vs. seller control.",
        ],
        key_terms=[
            KeyTermItem(
                term="Rejection Wick (Pin Bar)",
                definition="A candlestick characterized by a very long shadow (at least 2/3 of total candle length) and a small real body, indicating aggressive price rejection at a specific level.",
            ),
            KeyTermItem(
                term="Engulfing Candle",
                definition="A two-candle pattern where the real body of the second candle completely covers the real body of the preceding candle, signaling a decisive momentum shift.",
            ),
            KeyTermItem(
                term="Structural Confluence",
                definition="The simultaneous alignment of multiple independent technical factors (e.g., HTF support + session open + rejection candle) at a single price zone.",
            ),
        ],
        content_markdown="""### The Role of Candlesticks in Modern Trading

Candlesticks are visual representations of order flow during a discrete unit of time. However, novice traders often fall into the trap of memorizing dozens of candlestick names and executing trades whenever a pattern appears.

**The Golden Rule of Candlesticks:**
A candlestick pattern is **not a trading signal by itself**. It is merely a timing mechanism indicating how market participants reacted at a pre-existing level of interest.

---

### Core High-Probability Patterns

1. **Rejection Pin Bar (Hammer / Shooting Star):**
   - The long wick shows that price explored a territory, found an imbalance of counter-orders, and was violently driven back before the close.
   - A bullish pin bar at a major daily support level indicates institutional absorption of sell orders.
2. **Engulfing Bar (Bullish / Bearish):**
   - Demonstrates a decisive shift in control. The prior candle's range is completely overwhelmed by expanding volume.
3. **Inside Bar:**
   - A candle whose entire range is contained within the previous candle's High-Low range. Represents temporary consolidation before potential directional expansion.
""",
        hypothetical_example=HypotheticalExample(
            title="Evaluating Candlestick Context at Resistance",
            scenario="Trader X sees a shooting star rejection candle in the middle of a consolidating range on M5 and shorts immediately. Trader Y identifies a major H4 resistance zone at 1.3000 and waits for price to tap it before evaluating M15 candle response.",
            calculation="Trader X's pattern forms in no-man's land with no structural backing (random noise). Trader Y observes a bearish engulfing bar closing below 1.2990 after testing 1.3005 at the London Open.",
            outcome="Trader X gets stopped out as range chop continues. Trader Y enters with high confluence, tight stop above the wick (1.3012), targeting 1.2940 for a 1:2.5 R:R.",
            key_takeaway="Location on the chart dictates 80% of trade validity; the candlestick pattern provides only the remaining 20% for entry timing.",
        ),
        common_mistakes=[
            "Executing trades based solely on candlestick shapes appearing in the middle of chart ranges without structural context.",
            "Placing stop losses immediately at the candle wick tip without adding a spread cushion, leading to spread-widening stop-outs.",
            "Ignoring higher-timeframe candle closes in favor of lower-timeframe noise.",
        ],
        recap="Candlestick patterns are timing triggers, not standalone setups. Evaluate candle wicks and bodies only when they occur at pre-identified structural support and resistance levels.",
    ),
    # -------------------------------------------------------------------------
    # 4. Smart Money Concepts (SMC)
    # -------------------------------------------------------------------------
    CurriculumLessonDetail(
        id="smc-bos-choch-market-structure",
        slug="bos-choch-market-structure",
        title="Break of Structure (BOS) & Change of Character (CHoCH)",
        category_id="smc",
        category_title="Smart Money Concepts (SMC) Framework",
        short_description="Explore SMC structural transitions: Break of Structure (BOS) for trend continuation and Change of Character (CHoCH) for early trend shifts.",
        difficulty=DifficultyLevel.INTERMEDIATE,
        estimated_minutes=15,
        prerequisites=["ta-support-resistance-market-structure"],
        badge="[DISCRETIONARY FRAMEWORK]",
        learning_objectives=[
            "Define Break of Structure (BOS) and identify valid continuation breaks.",
            "Define Change of Character (CHoCH) and distinguish it from minor internal noise.",
            "Understand that SMC terminology describes standard price action through an institutional metaphor rather than an infallible predictive science.",
        ],
        key_terms=[
            KeyTermItem(
                term="Break of Structure (BOS)",
                definition="A price action event in Smart Money Concepts where price breaks and closes beyond a prior structural swing high (in an uptrend) or swing low (in a downtrend), signaling trend continuation.",
            ),
            KeyTermItem(
                term="Change of Character (CHoCH)",
                definition="The first break of a recent structural swing point in the opposing direction of the prevailing trend, interpreted as an early warning of a potential trend reversal.",
            ),
            KeyTermItem(
                term="Swing High / Swing Low",
                definition="A three-to-five bar structural pivot where the middle bar forms the highest high or lowest low relative to flanking bars.",
            ),
        ],
        content_markdown="""### What is Smart Money Concepts (SMC)?

Smart Money Concepts (SMC) is a discretionary price action framework popularized in retail trading communities. It reframes classical Dow Theory and Wyckoff market mechanics using terminology that metaphorically attributes market movements to "institutional algorithms" and "smart money."

> **Important Analytical Note:** While SMC provides a structured vocabulary for analyzing price charts, market participants must understand that it is an **interpretive heuristic framework**, not a mathematically proven scientific certainty. Markets move due to aggregate global supply, demand, macroeconomic realities, and institutional hedging—not an omniscient entity hunting individual retail micro-lots.

---

### Break of Structure (BOS): Trend Continuation

In an established trend:
- In a **Bullish Trend**, price forms a series of Higher Highs and Higher Lows. When price advances above the previous validated Swing High and **closes with a full candle body**, a **Bullish BOS** is confirmed.
- In a **Bearish Trend**, when price declines below the previous validated Swing Low and closes below it, a **Bearish BOS** is confirmed.

A valid BOS indicates that the prevailing order flow remains in control and subsequent pullbacks can be evaluated for continuation entries.

---

### Change of Character (CHoCH): Early Reversal Clue

A **Change of Character (CHoCH)** occurs when price breaks the structural pivot that initiated the most recent trend leg:
- In a downtrend, price has been printing Lower Highs (LH). When price rallies and breaks **above the most recent validated Lower High**, this structural disruption is labeled a **Bullish CHoCH**.
- It does not guarantee a new uptrend, but alerts the analyst that the downtrend has lost structural integrity.
""",
        hypothetical_example=HypotheticalExample(
            title="Differentiating BOS and CHoCH on 15-Minute Chart",
            scenario="GBP/USD is in an H1 downtrend with swings: LH1 at 1.2750 -> LL1 at 1.2680 -> LH2 at 1.2720 -> LL2 at 1.2640. Price then rallies sharply from 1.2640 and closes at 1.2730.",
            calculation="When price moved from 1.2680 down through 1.2640, it created a Bearish BOS (continuation). However, when price rallied from 1.2640 and closed at 1.2730, it closed ABOVE LH2 (1.2720). This represents a Bullish CHoCH.",
            outcome="The trader shifts their bias from aggressive trend-following selling to defensive neutral, monitoring for an SMC Order Block or Fair Value Gap near 1.2660 for a potential long retest.",
            key_takeaway="A CHoCH is an alert to pause opposing trades; confirmation from higher timeframes is essential before committing capital to a reversal thesis.",
        ),
        common_mistakes=[
            "Labeling every internal 1-minute wick break as a CHoCH, leading to continuous whiplash and overtrading.",
            "Requiring only a wick touch for BOS rather than waiting for a full candle body close to confirm structural commitment.",
            "Treating SMC as a guaranteed formula and abandoning strict position sizing rules.",
        ],
        recap="BOS confirms trend continuation; CHoCH provides an early warning of structural shift. Both must be validated with candle body closes on meaningful timeframes.",
    ),
    CurriculumLessonDetail(
        id="smc-order-blocks-fvg-liquidity",
        slug="order-blocks-fvg-liquidity",
        title="Order Blocks, Fair Value Gaps & Liquidity Sweeps",
        category_id="smc",
        category_title="Smart Money Concepts (SMC) Framework",
        short_description="Explore institutional footprint concepts: Order Blocks (OB), Fair Value Gaps (FVG) / Imbalances, and Buy-side/Sell-side liquidity sweeps.",
        difficulty=DifficultyLevel.INTERMEDIATE,
        estimated_minutes=16,
        prerequisites=["smc-bos-choch-market-structure"],
        badge="[DISCRETIONARY FRAMEWORK]",
        learning_objectives=[
            "Identify and map valid Bullish and Bearish Order Blocks (OB).",
            "Locate 3-candle Fair Value Gaps (FVG) and explain price rebalancing mechanics.",
            "Understand Buy-side Liquidity (BSL) and Sell-side Liquidity (SSL) pools and the mechanics of liquidity sweeps.",
        ],
        key_terms=[
            KeyTermItem(
                term="Order Block (OB)",
                definition="The last opposing candlestick prior to a strong, high-momentum displacement move that breaks market structure (BOS), interpreted as where large institutional positions were accumulated.",
            ),
            KeyTermItem(
                term="Fair Value Gap (FVG)",
                definition="A three-candle pattern where the middle candle creates an aggressive price displacement, leaving an unfilled space between Candle 1's wick and Candle 3's wick.",
            ),
            KeyTermItem(
                term="Liquidity Sweep (Stop Run)",
                definition="A rapid price excursion beyond a prominent swing high or low that triggers resting stop orders before aggressively reversing back into the trading range.",
            ),
        ],
        content_markdown="""### The Mechanics of Liquidity Pools

In any financial market, trading volume clusters around predictable chart zones:
- **Buy-Side Liquidity (BSL):** Resting stop-loss orders from short sellers and buy-stop breakout orders situated directly above prominent swing highs and double tops.
- **Sell-Side Liquidity (SSL):** Resting stop-loss orders from buyers and sell-stop breakout orders situated directly below prominent swing lows and double bottoms.

Institutional participants requiring large volume often utilize these concentrated liquidity pools to fill substantial orders without suffering excessive execution slippage.

---

### Order Blocks: The Footprint of Displacement

An **Order Block (OB)** is identified by two non-negotiable criteria:
1. It is the **last opposing candle** before an impulsive expansion move.
2. The expansion move **must cause a validated Break of Structure (BOS)** and create an imbalance (Fair Value Gap).

If an alleged Order Block does not lead to a structural break, it lacks institutional commitment and should be discarded.

---

### Fair Value Gaps (FVG) / Imbalances

An FVG is a three-candle sequence:
- **Candle 1:** Sets the initial high/low boundary.
- **Candle 2:** Large displacement candle showing massive unidirectional volume.
- **Candle 3:** Subsequent candle whose wick does not overlap with Candle 1.

The empty zone between Candle 1's wick and Candle 3's wick is the **Fair Value Gap**. SMC theory posits that price tends to retrace back into this void to "rebalance" price efficiency before resuming directional expansion.
""",
        hypothetical_example=HypotheticalExample(
            title="Trading a Bullish Order Block + FVG Confluence Setup",
            scenario="EUR/USD on M15 breaks above a major resistance level at 1.0850 with a massive green expansion candle, creating a BOS. The last red candle before this rally was at 1.0825 - 1.0835. An FVG exists between 1.0838 and 1.0845.",
            calculation="Order Block Zone: 1.0825 - 1.0835.\nTrader places a Buy Limit at 1.0835 (top of OB), with Stop Loss at 1.0818 (17 pips, below the OB low). Take Profit target is set at recent BSL high at 1.0886 (51 pips).",
            outcome="Price retraces into the FVG and mitigates the upper boundary of the Order Block at 1.0835, fills the order, and resumes the upward rally to 1.0886, delivering a 1:3 R:R outcome.",
            key_takeaway="Order blocks are effective only when paired with displacement and structural breaks; mitigating an OB without higher-timeframe context carries high failure rates.",
        ),
        common_mistakes=[
            "Marking every opposing candle on the chart as an Order Block, resulting in 'analysis paralysis'.",
            "Assuming every FVG must be filled immediately (some FVGs remain unfilled for weeks or indefinitely during strong macroeconomic trends).",
            "Entering trades before price visibly rejects an OB or FVG on lower timeframes.",
        ],
        recap="Order Blocks mark the origin of displacement; Fair Value Gaps represent volume imbalances; liquidity sweeps clear resting orders. Use these tools as structured entry filters rather than infallible dogmas.",
    ),
    # -------------------------------------------------------------------------
    # 5. Inner Circle Trader (ICT)
    # -------------------------------------------------------------------------
    CurriculumLessonDetail(
        id="ict-sessions-killzones-ote",
        slug="sessions-killzones-ote",
        title="ICT Kill Zones, Optimal Trade Entry (OTE) & Judas Swing",
        category_id="ict",
        category_title="Inner Circle Trader (ICT) Framework",
        short_description="Objectively analyze ICT time-based frameworks: Session Kill Zones, the Judas Swing liquidity raid, and Fibonacci Optimal Trade Entry (OTE).",
        difficulty=DifficultyLevel.ADVANCED,
        estimated_minutes=16,
        prerequisites=["smc-order-blocks-fvg-liquidity", "fx-market-sessions-order-types"],
        badge="[DISCRETIONARY FRAMEWORK]",
        learning_objectives=[
            "Identify the specific timing windows for ICT London and New York Kill Zones.",
            "Understand the mechanics of the 'Judas Swing' false breakout at session opens.",
            "Apply the Optimal Trade Entry (OTE) Fibonacci retracement model (0.62 to 0.79).",
            "Maintain an objective perspective distinguishing trading heuristics from unverified algorithmic conspiracy claims.",
        ],
        key_terms=[
            KeyTermItem(
                term="Kill Zone",
                definition="High-probability time windows in ICT methodology where session opens trigger peak volatility and institutional order rebalancing (e.g., London Open Kill Zone: 02:00-05:00 EST).",
            ),
            KeyTermItem(
                term="Judas Swing",
                definition="An engineered deceptive initial move at the start of a trading session designed to sweep liquidity and trap retail traders on the wrong side before the true session trend commences.",
            ),
            KeyTermItem(
                term="Optimal Trade Entry (OTE)",
                definition="A Fibonacci retracement zone between 61.8% (0.62) and 78.6% (0.79), with 70.5% considered the optimal midpoint for entering in the direction of order flow.",
            ),
        ],
        content_markdown="""### The Time-and-Price Philosophy

The Inner Circle Trader (ICT) methodology emphasizes that **time is equal to or more important than price**. While technical indicators focus solely on past price data, ICT models anchor setups to specific institutional trading hours known as **Kill Zones**.

#### Key Session Kill Zones (EST / New York Time)
1. **London Open Kill Zone:** 02:00 - 05:00 EST (07:00 - 10:00 GMT). Often establishes the High or Low of the daily candle.
2. **New York Open Kill Zone:** 07:00 - 10:00 EST (12:00 - 15:00 GMT). Drives major continuation or midday reversal coinciding with US macroeconomic releases.
3. **London Close Kill Zone:** 10:00 - 12:00 EST. Typically marks profit-taking and retracement of the daily expansion.

---

### The Judas Swing: Anatomy of Session Open Manipulation

A frequent market phenomenon observed at the London Open is the **Judas Swing**:
1. During the Asian session, price consolidates, establishing clear Asian Highs and Lows.
2. In the first 30–60 minutes of the London Open, price makes an aggressive, rapid thrust *downward*, breaking below the Asian Low.
3. Novice breakout traders interpret this as a bearish breakout and enter short.
4. In reality, this move sweeps resting Sell-Side Liquidity. Price abruptly halts, prints an M5/M15 displacement reversal, and embarks on a massive bullish rally for the remainder of the London session.

---

### Optimal Trade Entry (OTE)

The **OTE model** identifies retracements within an impulsive displacement swing:
- Anchor the Fibonacci tool from the **Swing Low to Swing High** (for bullish continuation).
- The primary entry target is the **0.62 to 0.79 retracement bracket**, with the **0.705 level** serving as the optimal sweet spot.
- Confluence with a Fair Value Gap or Order Block within this 0.62-0.79 zone provides the highest probability setup.
""",
        hypothetical_example=HypotheticalExample(
            title="Executing a London Open Judas Swing + OTE Setup",
            scenario="EUR/USD trades within an Asian session range of 1.0820 (Low) to 1.0850 (High). At 02:30 EST, price spikes down to 1.0810 (sweeping Asian Low), then immediately reverses with a strong 15-minute bullish candle closing at 1.0860 (breaking Asian High).",
            calculation="Displacement swing: Low = 1.0810, High = 1.0860 (50 pips).\nOTE Fib levels: 0.62 = 1.0829, 0.705 = 1.0825, 0.79 = 1.0820.\nTrader places Buy Limit at 1.0827 (aligned with a 15m FVG), Stop Loss at 1.0805 (below the Judas swing low, 22 pips risk). Target: 1.0893 (66 pips gain).",
            outcome="Price pulls back smoothly into 1.0826 during the London Kill Zone, fills the order, and expands upward toward target, achieving a 1:3 R:R.",
            key_takeaway="Waiting for the initial session manipulation to complete before entering on the secondary retracement drastically reduces drawdown.",
        ),
        common_mistakes=[
            "Chasing the initial breakout at 02:00 or 08:00 EST and becoming the liquidity for the Judas Swing reversal.",
            "Treating the OTE Fibonacci levels as magic barriers rather than looking for underlying order blocks or FVGs inside the zone.",
            "Subscribing to conspiratorial views that 'central banks are hunting your 0.05 lot order' instead of recognizing universal liquidity pooling.",
        ],
        recap="ICT integrates precise time windows (Kill Zones) with price displacement. Identifying the Judas Swing and entering via the OTE Fibonacci bracket (62%-79%) provides a structured timing blueprint.",
    ),
    CurriculumLessonDetail(
        id="ict-market-maker-models-amd",
        slug="market-maker-models-amd",
        title="Market Maker Models & AMD (Accumulation, Manipulation, Distribution)",
        category_id="ict",
        category_title="Inner Circle Trader (ICT) Framework",
        short_description="Analyze the Power of Three (AMD) framework and Market Maker Buy/Sell Models (MMBM/MMSM) with empirical rigor.",
        difficulty=DifficultyLevel.ADVANCED,
        estimated_minutes=15,
        prerequisites=["ict-sessions-killzones-ote"],
        badge="[DISCRETIONARY FRAMEWORK]",
        learning_objectives=[
            "Explain the Power of Three (AMD): Accumulation, Manipulation, and Distribution.",
            "Recognize the structural phases of the Market Maker Buy Model (MMBM) and Market Maker Sell Model (MMSM).",
            "Synthesize ICT concepts with standard macroeconomic and liquidity awareness.",
        ],
        key_terms=[
            KeyTermItem(
                term="Power of Three (AMD)",
                definition="A conceptual model describing the formation of a daily candlestick: Accumulation (open/range), Manipulation (false move beyond open), and Distribution (real trend expansion to close).",
            ),
            KeyTermItem(
                term="Market Maker Buy Model (MMBM)",
                definition="A multi-stage structural curve starting with consolidation, moving through a downward distribution curve, culminating in a Smart Money Reversal, and expanding up into an accumulation curve.",
            ),
            KeyTermItem(
                term="Smart Money Reversal (SMR)",
                definition="The pivotal inflection point in a Market Maker Model where price sweeps a key liquidity pool, creates a CHoCH, and inverts directional order flow.",
            ),
        ],
        content_markdown="""### The Power of Three (AMD)

The **Power of Three (AMD)** model breaks down the life-cycle of a classic directional trading day:

1. **Accumulation:**
   - Typically occurs during the Asian session and early London pre-market.
   - Price trades in a tight range near the day's opening price as smart money accumulates directional orders.
2. **Manipulation (The Trap):**
   - Occurs near the London Open. Price pushes deceptively in the direction opposite to the intended daily trend.
   - On a bullish day: Price drops below the daily open price to create the Low of the Day (LOD).
   - On a bearish day: Price rallies above the daily open price to create the High of the Day (HOD).
3. **Distribution:**
   - The sustained expansion phase across the London and New York sessions.
   - Price delivers value aggressively toward opposing liquidity targets, finally closing near the extreme of the candle.

---

### Market Maker Models: Symmetrical Curves

The **Market Maker Buy Model (MMBM)** and **Market Maker Sell Model (MMSM)** illustrate how liquidity is engineered on both sides of a market curve:
- **Original Consolidation:** The initial range that defines the ultimate objective of the model.
- **Drive Phase:** Price engineers a series of lower highs and lower lows (in MMBM) to accumulate buy-side liquidity above.
- **Smart Money Reversal (SMR):** Rejection of a higher-timeframe key level with displacement.
- **Buy/Sell Side Curve:** Price re-engineers each previous level of the drive phase, systematically targeting the original consolidation.
""",
        hypothetical_example=HypotheticalExample(
            title="Identifying AMD on a Daily Candlestick",
            scenario="Daily EUR/USD open is 1.0800. Daily bias is strongly bullish based on weekly support. At 03:00 EST, price pushes down to 1.0775 (Manipulation below daily open).",
            calculation="Daily Open: 1.0800.\nManipulation: Low printed at 1.0775 (-25 pips from open).\nReversal: Price reclaims 1.0800 by 04:00 EST with an H1 BOS.\nDistribution Target: Daily High target resting at 1.0880 (+80 pips from open).",
            outcome="A trader buys the re-entry above 1.0800 with stop loss at 1.0770 (30 pips risk), targeting 1.0880 (80 pips gain). Daily candle closes at 1.0875 as a classic wide-range bullish Marubozu with small lower wick.",
            key_takeaway="Understanding AMD keeps you aligned with the daily candle expansion rather than getting caught in early morning noise.",
        ),
        common_mistakes=[
            "Labeling every random pullback as 'manipulation' instead of recognizing normal liquidity repricing.",
            "Attempting to trade the SMR reversal prematurely before price confirms a structural shift with displacement.",
            "Over-complicating trading plans with unnecessary jargon when simple price action and risk management suffice.",
        ],
        recap="AMD (Accumulation, Manipulation, Distribution) provides a structural framework for understanding daily candle dynamics. SMR marks the pivot from liquidity gathering to directional trend expansion.",
    ),
    # -------------------------------------------------------------------------
    # 6. Trading Psychology & Discipline
    # -------------------------------------------------------------------------
    CurriculumLessonDetail(
        id="psych-emotional-cycle-fomo-revenge",
        slug="emotional-cycle-fomo-revenge",
        title="The Emotional Cycle, FOMO & Revenge Trading",
        category_id="psychology",
        category_title="Trading Psychology & Behavioral Discipline",
        short_description="Examine the neurobiology of trading stress, how fear of missing out triggers late entries, and the catastrophic mechanics of revenge trading.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=12,
        prerequisites=["risk-drawdown-recovery-math"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Identify the psychological and biological triggers of Fear of Missing Out (FOMO).",
            "Recognize revenge trading behavior and rapid re-entry patterns immediately upon onset.",
            "Implement somatic and operational circuit-breakers to halt emotional decision-making.",
        ],
        key_terms=[
            KeyTermItem(
                term="FOMO (Fear of Missing Out)",
                definition="An intense emotional anxiety that others are profiting while you are left behind, compelling traders to enter impulsive trades without setup confirmation.",
            ),
            KeyTermItem(
                term="Revenge Trading",
                definition="The act of opening aggressive, oversized trades immediately following a loss in an emotional attempt to 'win back' lost capital and restore ego.",
            ),
            KeyTermItem(
                term="Amygdala Hijack",
                definition="A biological state where acute stress floods the brain with cortisol and adrenaline, temporarily disabling prefrontal cortex executive reasoning and risk assessment.",
            ),
        ],
        content_markdown="""### The Neurobiology of Trading Losses

Financial risk triggers the human brain's primal survival apparatus. When you experience a monetary loss, your brain does not perceive it as an abstract statistical event; it perceives it as a **direct existential threat**, triggering an acute **fight-or-flight response**:

1. **Cortisol and Adrenaline Spike:** Your heart rate elevates, muscles tense, and visual focus narrows.
2. **Prefrontal Cortex Inhibition:** The rational, analytical prefrontal cortex—the part of the brain responsible for risk calculation and rules adherence—is effectively hijacked by the emotional amygdala.
3. **The Ego Threat:** Losses are internalized as personal failures or humiliations rather than routine business expenses.

In this compromised biological state, the trader feels an overwhelming impulse to take immediate action: **Revenge Trading**.

---

### The Anatomy of Revenge Trading

A typical revenge trading sequence follows a rapid, destructive cascade:
1. **Initial Controlled Loss:** Trader loses -$100 on an EUR/USD trade following their rules.
2. **Frustration / Invalidation:** Feeling cheated by the market, the trader enters again within 2 minutes with double the lot size (lot swelling).
3. **Compounding Losses:** The second trade loses -$200. Total loss is now -$300.
4. **Panic & Complete Rule Dissolution:** The trader enters a massive 5.0 lot position with no stop loss. A 20-pip adverse move results in a -$1,000 loss, blowing a month of disciplined gains in twenty minutes.

---

### Overcoming FOMO: The Abundance Mindset

FOMO is driven by the illusion of scarcity—the belief that "if I don't get in right now, I will miss the trade of the month."
- **The Institutional Truth:** The global foreign exchange market transacts over **$7.5 Trillion every single day**.
- High-probability trading opportunities are virtually infinite; your account capital is strictly finite.
- Missing a trade costs exactly **$0.00**. Chasing a trade in FOMO costs your account balance and mental capital.
""",
        hypothetical_example=HypotheticalExample(
            title="Recognizing Rapid Re-entry After Loss (Behavioral Audit)",
            scenario="A trader loses $150 on GBP/JPY at 09:15 EST. At 09:17 EST, they open a new GBP/JPY position with 2.0x normal lot size without an updated checklist or structural invalidation.",
            calculation="Normal risk: 1.0% ($150). Revenge trade risk: 2.5% ($375) with no defined stop loss. Price continues against them for 35 pips. Loss = -$875. Total loss in 30 minutes = -$1,025 (over 6.8x normal risk).",
            outcome="The trader has committed two major behavioral violations: Rapid Re-Entry (<15 min after loss) and Lot Size Swelling.",
            key_takeaway="Implement an enforced operational rule: after any loss, you must step away from the trading terminal for a mandatory 15-minute cool-down period.",
        ),
        common_mistakes=[
            "Remaining glued to the screen immediately after a painful loss, actively looking for any excuse to re-enter.",
            "Viewing trading as an intellectual battle against the broker or market rather than an internal exercise in probability management.",
            "Celebrating oversized lucky wins, which psychologically conditions you to repeat undisciplined behavior.",
        ],
        recap="Emotional trading is rooted in biological stress responses. Losses must be accepted as statistical variance. Enforce mandatory cool-down periods to prevent revenge trading spirals.",
    ),
    CurriculumLessonDetail(
        id="psych-journaling-discipline-process",
        slug="journaling-discipline-process",
        title="Institutional Journaling & The Law of Process",
        category_id="psychology",
        category_title="Trading Psychology & Behavioral Discipline",
        short_description="Master the art of high-density trade journaling, objective post-trade audits, and prioritizing process over outcome.",
        difficulty=DifficultyLevel.BEGINNER,
        estimated_minutes=14,
        prerequisites=["psych-emotional-cycle-fomo-revenge"],
        badge="[EDUCATIONAL CONTENT]",
        learning_objectives=[
            "Construct an institutional trade journal documenting strategy, psychology, and R-multiples.",
            "Distinguish between good decisions with losing outcomes and bad decisions with winning outcomes.",
            "Conduct structured weekly behavioral self-audits to eliminate recurring performance leaks.",
        ],
        key_terms=[
            KeyTermItem(
                term="Trade Journal",
                definition="A comprehensive, objective record of every executed trade, capturing technical entry criteria, planned vs. realized R:R, screenshots, emotional state, and rule adherence.",
            ),
            KeyTermItem(
                term="Process vs. Outcome",
                definition="The principle that in probabilistic environments with high variance, trade quality must be judged exclusively by adherence to rules, not by whether an individual trade won or lost money.",
            ),
            KeyTermItem(
                term="R-Multiple",
                definition="The metric measuring trade outcome expressed as a multiple of initial risk (e.g., +2.5R means a profit equal to 2.5 times the stop-loss risk).",
            ),
        ],
        content_markdown="""### The Paradox of Process vs. Outcome

In traditional professions, results correlate directly with immediate outcomes: if a surgeon performs a procedure correctly, the patient survives. In trading, however, **variance and randomness decouple immediate outcomes from execution quality**:

- **Good Trade / Losing Outcome:** You followed your playbook flawlessly, waited for all confirmations, sized your risk at 1.0%, and placed your stop-loss correctly. A sudden surprise news headline stops you out for -1.0R. **This was an excellent trade.**
- **Bad Trade / Winning Outcome:** You traded out of boredom, risked 25% of your account with no stop loss, and market noise happened to spike in your favor, yielding a +50% gain. **This was a catastrophic trade**, because it reinforced toxic behavior that will inevitably liquidate your account.

---

### What Institutional Traders Journal

A professional trade journal (such as the AI Trading Copilot journal) captures data across four dimensions:

1. **Pre-Trade Context:** Currency pair, session, higher-timeframe trend, technical setup classification (SMC, ICT, Price Action), and checklist confirmation.
2. **Mathematical Metrics:** Exact entry price, stop-loss price, take-profit price, lot size, dollar risk, and planned R:R ratio.
3. **Psychological & Emotional State:** Were you calm, anxious, hurried, or experiencing FOMO? Rate your emotional discipline from 1 to 5.
4. **Post-Trade Execution Audit:** Did you move your stop? Did you exit early? Did you follow your planned exit criteria? What was the realized R-multiple?
""",
        hypothetical_example=HypotheticalExample(
            title="The True Value of a 50-Trade Journal Audit",
            scenario="A trader reviews their past 50 trades in their AI Trading Copilot journal. Overall P&L is breakeven ($0).",
            calculation="Upon filtering by tag, the journal reveals:\n- Trades taken between 08:00-11:00 EST adhering to ICT setup: 28 trades, 57% win rate, Net +$3,200 (+12.8R).\n- Trades taken after 14:00 EST or on weekends: 22 trades, 18% win rate, Net -$3,200 (-13.0R), with 80% flagged as 'Rapid Re-entry'.",
            outcome="The data proves conclusively that the core strategy is highly profitable, but after-hours boredom trades are siphoning away 100% of the profits.",
            key_takeaway="Without a structured journal, the trader would assume their strategy failed; with a journal, they simply eliminate afternoon trades and immediately become consistently profitable.",
        ),
        common_mistakes=[
            "Journaling only winning trades while ignoring losses due to shame or emotional denial.",
            "Recording only entry and exit prices without documenting emotional state or setup context.",
            "Collecting hundreds of journal entries but never performing a periodic analytical review to identify behavioral leaks.",
        ],
        recap="Trade quality is defined by process discipline, not individual outcome. Maintaining a comprehensive journal and conducting data-driven behavioral audits is the single most reliable path to consistency.",
    ),
]

# -----------------------------------------------------------------------------
# Curated External Resources (Vetted, Official, No Referral Links, No Fabrications)
# -----------------------------------------------------------------------------
CURATED_RESOURCES: list[CuratedResourceResponse] = [
    CuratedResourceResponse(
        id="cftc-forex-basics",
        title="CFTC Forex Basics: What Currency Traders Should Know",
        publisher="U.S. Commodity Futures Trading Commission (CFTC)",
        topic="Market Mechanics & Regulation",
        difficulty=DifficultyLevel.BEGINNER,
        cost=CostClassification.FREE,
        resource_type=ResourceType.DOCUMENTATION,
        url="https://www.cftc.gov/LearnAndProtect/EducationCenter/CustomerAdvisories/forex.html",
        description="Official regulatory customer advisory explaining retail forex market structure, leverage limitations, execution risks, and consumer fraud protection.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="bis-triennial-survey",
        title="BIS Triennial Central Bank Survey: Foreign Exchange Turnover",
        publisher="Bank for International Settlements (BIS)",
        topic="Market Mechanics & Regulation",
        difficulty=DifficultyLevel.INTERMEDIATE,
        cost=CostClassification.FREE,
        resource_type=ResourceType.DOCUMENTATION,
        url="https://www.bis.org/statistics/rpfx22.htm",
        description="The authoritative global benchmark report detailing total foreign exchange turnover, market participant distribution, and instrument breakdown.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="babypips-school-pipsology",
        title="School of Pipsology",
        publisher="BabyPips.com",
        topic="Forex Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        cost=CostClassification.FREE,
        resource_type=ResourceType.COURSE,
        url="https://www.babypips.com/learn/forex",
        description="Widely acclaimed beginner curriculum covering currency pairs, pips, candlestick basics, session overlaps, and foundational technical analysis.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="investopedia-risk-management",
        title="Forex Risk Management: Principles and Strategies",
        publisher="Investopedia",
        topic="Risk Management",
        difficulty=DifficultyLevel.BEGINNER,
        cost=CostClassification.FREE,
        resource_type=ResourceType.ARTICLE,
        url="https://www.investopedia.com/articles/forex/07/manage_risk.asp",
        description="Comprehensive guide outlining stop-loss placement, position sizing, leverage management, and portfolio capital preservation techniques.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="investopedia-position-sizing",
        title="Calculating Risk and Position Size in Forex Trading",
        publisher="Investopedia",
        topic="Risk Management",
        difficulty=DifficultyLevel.BEGINNER,
        cost=CostClassification.FREE,
        resource_type=ResourceType.ARTICLE,
        url="https://www.investopedia.com/articles/forex/06/positionsizing.asp",
        description="Practical tutorial detailing the step-by-step mathematical calculations required to derive exact lot sizes from stop loss pips and account equity.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="trading-in-the-zone",
        title="Trading in the Zone: Master the Market with Confidence and Discipline",
        publisher="Mark Douglas (Penguin Random House)",
        topic="Trading Psychology",
        difficulty=DifficultyLevel.INTERMEDIATE,
        cost=CostClassification.PAID,
        resource_type=ResourceType.BOOK,
        url="https://www.penguinrandomhouse.com/books/297298/trading-in-the-zone-by-mark-douglas/",
        description="Seminal work on the psychology of probabilistic thinking, emotional mastery, overcoming the fear of losing, and developing institutional trading consistency. Consult official bookseller for regional pricing.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="daily-trading-coach",
        title="The Daily Trading Coach: 101 Lessons for Self-Coaching",
        publisher="Brett N. Steenbarger, Ph.D. (John Wiley & Sons)",
        topic="Trading Psychology",
        difficulty=DifficultyLevel.INTERMEDIATE,
        cost=CostClassification.PAID,
        resource_type=ResourceType.BOOK,
        url="https://www.wiley.com/en-us/The+Daily+Trading+Coach%3A+101+Lessons+for+Becoming+Your+Own+Trading+Psychologist-p-9780470423608",
        description="Cognitive-behavioral psychological strategies, performance tracking exercises, and mental frameworks from a renowned institutional trading psychologist.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="murphy-technical-analysis",
        title="Technical Analysis of the Financial Markets",
        publisher="John J. Murphy (New York Institute of Finance)",
        topic="Technical Analysis",
        difficulty=DifficultyLevel.INTERMEDIATE,
        cost=CostClassification.PAID,
        resource_type=ResourceType.BOOK,
        url="https://www.penguinrandomhouse.com/books/330541/technical-analysis-of-the-financial-markets-by-john-j-murphy/",
        description="The definitive standard textbook covering chart construction, trendlines, support and resistance, price patterns, and time cycles.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="mt5-official-docs",
        title="MetaTrader 5 Client Terminal User Guide",
        publisher="MetaQuotes Software Corp.",
        topic="Forex Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        cost=CostClassification.FREE,
        resource_type=ResourceType.DOCUMENTATION,
        url="https://www.metatrader5.com/en/terminal/help",
        description="Official documentation covering MT5 execution modes, pending order types, depth of market, deal records, and platform settings.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="cme-education-fx",
        title="Introduction to FX Market Mechanics & Currency Futures",
        publisher="CME Group Education",
        topic="Market Mechanics & Regulation",
        difficulty=DifficultyLevel.INTERMEDIATE,
        cost=CostClassification.FREE,
        resource_type=ResourceType.COURSE,
        url="https://www.cmegroup.com/education.html",
        description="CME Group foundational education exploring currency futures specifications, centralized clearing versus OTC spot markets, and volume dynamics.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="ny-fed-fx-committee",
        title="FX Global Code: Principles of Good Practice",
        publisher="Foreign Exchange Committee (Federal Reserve Bank of New York)",
        topic="Market Mechanics & Regulation",
        difficulty=DifficultyLevel.ADVANCED,
        cost=CostClassification.FREE,
        resource_type=ResourceType.DOCUMENTATION,
        url="https://www.newyorkfed.org/fxc",
        description="A set of global principles of good practice in the foreign exchange market to promote integrity, transparency, and liquidity standards.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="investopedia-candlesticks",
        title="An Introduction to Candlestick Chart Patterns",
        publisher="Investopedia",
        topic="Technical Analysis",
        difficulty=DifficultyLevel.BEGINNER,
        cost=CostClassification.FREE,
        resource_type=ResourceType.ARTICLE,
        url="https://www.investopedia.com/trading/candlestick-charting-what-is-it/",
        description="Clear educational primer on candlestick construction, real bodies, wicks, and how to read buyer vs seller control without relying on standalone patterns.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="smc-educational-overview",
        title="Smart Money Concepts (SMC): A Structural Overview",
        publisher="BabyPips / Market Structure Education",
        topic="Smart Money Concepts",
        difficulty=DifficultyLevel.INTERMEDIATE,
        cost=CostClassification.FREE,
        resource_type=ResourceType.ARTICLE,
        url="https://www.babypips.com/learn/forex/market-structure",
        description="Neutral breakdown of Break of Structure (BOS), Change of Character (CHoCH), and Order Blocks as price action heuristics rather than predictive guarantees.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
    CuratedResourceResponse(
        id="metaquotes-order-types-guide",
        title="MetaQuotes Guide: Order Types & Execution Mechanics",
        publisher="MetaQuotes Software Corp.",
        topic="Forex Fundamentals",
        difficulty=DifficultyLevel.BEGINNER,
        cost=CostClassification.FREE,
        resource_type=ResourceType.DOCUMENTATION,
        url="https://www.metatrader5.com/en/terminal/help/trading_general/orders",
        description="Official technical reference detailing market execution, pending buy/sell limits, buy/sell stops, stop-limit orders, and execution policies.",
        language="en",
        verified=True,
        last_reviewed="2025-01-15",
        badge="[VERIFIED RESOURCE]",
    ),
]
