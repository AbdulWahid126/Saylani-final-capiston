"""Pydantic v2 schemas for deterministic financial analytics engine."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RatioAssumptions(BaseModel):
    """Explicitly documented assumptions for risk-adjusted return ratios."""

    model_config = ConfigDict(frozen=True)

    return_series: str = Field(
        default="per_trade_net_pnl_pct",
        description="Return definition used (e.g., 'per_trade_net_pnl_pct', 'per_trade_monetary').",
    )
    risk_free_rate_annual: float = Field(
        default=0.0,
        description="Assumed annual risk-free rate (e.g., 0.0 for 0%).",
    )
    risk_free_rate_per_period: float = Field(
        default=0.0,
        description="Effective risk-free rate per period/trade.",
    )
    downside_deviation_target: float = Field(
        default=0.0,
        description="Minimum Acceptable Return (MAR) target for downside deviation.",
    )
    is_annualized: bool = Field(
        default=False,
        description="Whether the ratio has been annualized.",
    )
    annualization_notes: str = Field(
        default="Unannualized per-trade ratio. Trades occur at irregular intraday intervals; annualization without defensible trade frequency is omitted.",
        description="Methodological notes explaining annualization choice.",
    )


class CategoryBreakdownItem(BaseModel):
    """Performance breakdown summary for a specific dimension category."""

    category: str = Field(description="Category label (e.g. 'EURUSD', 'BUY', 'LONDON', 'Monday').")
    total_trades: int = Field(ge=0, description="Total closed trades in this category.")
    wins: int = Field(ge=0, description="Winning trades count.")
    losses: int = Field(ge=0, description="Losing trades count.")
    breakevens: int = Field(ge=0, description="Breakeven trades count.")
    win_rate: float = Field(ge=0.0, le=100.0, description="Win rate percentage.")
    gross_profit: float = Field(description="Gross profit from winning trades in account currency.")
    gross_loss: float = Field(
        description="Gross loss magnitude from losing trades in account currency."
    )
    net_pnl: float = Field(description="Net realized P&L including commission and swap.")
    profit_factor: float | None = Field(
        default=None,
        description="Profit factor (gross profit / gross loss). None if zero losses.",
    )
    average_trade: float = Field(description="Average net P&L per trade in account currency.")


class AnalyticsBreakdownsResponse(BaseModel):
    """Comprehensive performance breakdowns across trading dimensions."""

    by_symbol: list[CategoryBreakdownItem] = Field(default_factory=list)
    by_direction: list[CategoryBreakdownItem] = Field(default_factory=list)
    by_session: list[CategoryBreakdownItem] = Field(default_factory=list)
    by_day_of_week: list[CategoryBreakdownItem] = Field(default_factory=list)
    by_hour_of_day: list[CategoryBreakdownItem] = Field(default_factory=list)
    by_strategy: list[CategoryBreakdownItem] = Field(default_factory=list)


class EquityPoint(BaseModel):
    """Single chronological point along the account equity & cumulative P&L curve."""

    point_index: int = Field(ge=0, description="Chronological sequence index starting at 0.")
    timestamp: datetime = Field(
        description="Timestamp of point (start time for index 0, close time for trades)."
    )
    trade_id: str | None = Field(
        default=None, description="UUID of trade closing at this point, None for baseline."
    )
    balance: float = Field(description="Account balance after trade settlement.")
    equity: float = Field(description="Account closed equity after trade settlement.")
    cumulative_pnl: float = Field(description="Cumulative net realized P&L from starting point.")
    peak_equity: float = Field(description="High-water mark equity up to this point.")
    drawdown_monetary: float = Field(ge=0.0, description="Monetary drawdown from peak ($ amount).")
    drawdown_percentage: float = Field(
        ge=0.0, le=100.0, description="Percentage drawdown from peak (%)."
    )


class EquityCurveResponse(BaseModel):
    """Chronological equity curve time series response."""

    account_id: uuid.UUID | None = Field(default=None)
    currency: str = Field(default="USD")
    initial_balance: float = Field(ge=0.0)
    current_equity: float = Field(description="Final closed equity at the end of the series.")
    total_net_pnl: float = Field(description="Sum of all realized net P&L in the series.")
    max_drawdown_monetary: float = Field(ge=0.0, description="Maximum monetary drawdown observed.")
    max_drawdown_percentage: float = Field(
        ge=0.0, le=100.0, description="Maximum percentage drawdown observed."
    )
    points: list[EquityPoint] = Field(default_factory=list)


class PerformanceMetrics(BaseModel):
    """Comprehensive deterministic financial analytics summary."""

    # Scope & Baseline
    currency: str = Field(default="USD", description="Base currency of the reporting account(s).")
    initial_balance: float = Field(ge=0.0, description="Initial balance baseline used.")
    closed_equity: float = Field(description="Current equity based on closed trade results.")

    # Trade Counts
    total_trades: int = Field(ge=0, description="Total closed trades evaluated.")
    winning_trades: int = Field(ge=0, description="Number of closed trades with net_pnl > 0.")
    losing_trades: int = Field(ge=0, description="Number of closed trades with net_pnl < 0.")
    breakeven_trades: int = Field(ge=0, description="Number of closed trades with net_pnl == 0.")
    open_trades_count: int = Field(
        ge=0, description="Number of currently open/partial positions (excluded from closed stats)."
    )

    # Rates (%)
    win_rate: float = Field(ge=0.0, le=100.0, description="Percentage of winning closed trades.")
    loss_rate: float = Field(ge=0.0, le=100.0, description="Percentage of losing closed trades.")
    breakeven_rate: float = Field(
        ge=0.0, le=100.0, description="Percentage of breakeven closed trades."
    )

    # Monetary Totals
    gross_profit: float = Field(ge=0.0, description="Sum of positive trade gains.")
    gross_loss: float = Field(ge=0.0, description="Magnitude (positive value) of trade losses.")
    net_pnl: float = Field(
        description="Net realized P&L = gross_profit - gross_loss + commissions + swaps."
    )
    total_commission: float = Field(description="Total broker commissions paid.")
    total_swap: float = Field(description="Total overnight financing swaps paid/received.")

    # Per-Trade Averages & Ratios
    average_win: float = Field(ge=0.0, description="Average net gain on winning trades.")
    average_loss: float = Field(ge=0.0, description="Average net loss magnitude on losing trades.")
    win_loss_ratio: float | None = Field(
        default=None,
        description="Average win / Average loss ratio. None if zero losses.",
    )
    profit_factor: float | None = Field(
        default=None,
        description="Gross Profit / Gross Loss. None if zero losses (safe division).",
    )
    expectancy_per_trade: float = Field(
        description="Expected net P&L per trade (Net P&L / Total Trades).",
    )

    # Streaks
    max_consecutive_wins: int = Field(ge=0, description="Longest consecutive winning trade streak.")
    max_consecutive_losses: int = Field(
        ge=0, description="Longest consecutive losing trade streak."
    )
    current_streak: int = Field(
        description="Current active streak (positive for wins, negative for losses, 0 for none).",
    )

    # Risk & Drawdown
    max_drawdown_monetary: float = Field(
        ge=0.0, description="Maximum peak-to-trough drop in currency units."
    )
    max_drawdown_percentage: float = Field(
        ge=0.0, le=100.0, description="Maximum peak-to-trough drop as a percentage."
    )

    # Risk-Adjusted Ratios & Documented Assumptions
    sharpe_ratio: float | None = Field(
        default=None,
        description="Sharpe ratio. None if insufficient data (N < 2) or zero variance.",
    )
    sortino_ratio: float | None = Field(
        default=None,
        description="Sortino ratio. None if insufficient data (N < 2) or zero downside deviation.",
    )
    ratio_assumptions: RatioAssumptions = Field(
        default_factory=RatioAssumptions,
        description="Documented assumptions for Sharpe and Sortino calculations.",
    )


class AnalyticsSummaryResponse(BaseModel):
    """Full API response for analytics summary endpoint."""

    account_id: uuid.UUID | None = Field(default=None)
    account_number: str | None = Field(default=None)
    broker_name: str | None = Field(default=None)
    from_date: datetime | None = Field(default=None)
    to_date: datetime | None = Field(default=None)
    metrics: PerformanceMetrics
