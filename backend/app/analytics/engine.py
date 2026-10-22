"""Deterministic Financial Analytics Engine.

Calculates key performance metrics, chronological equity curve, maximum drawdown,
Sharpe and Sortino ratios, and multidimensional breakdowns using pure deterministic
Python and NumPy mathematics.

ZERO LLM MATH: LLMs are strictly forbidden from calculating or estimating financial statistics.
"""

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.models.journal import JournalEntry
from app.schemas.analytics import (
    AnalyticsBreakdownsResponse,
    CategoryBreakdownItem,
    EquityCurveResponse,
    EquityPoint,
    PerformanceMetrics,
    RatioAssumptions,
)


@dataclass(frozen=True)
class TradeRecord:
    """Immutable, typed normalized record representing a single closed trade."""

    id: str
    account_id: str
    symbol: str
    direction: str
    volume: float
    entry_price: float
    exit_price: float | None
    gross_profit: float
    commission: float
    swap: float
    net_pnl: float
    open_time: datetime
    close_time: datetime
    status: str
    session: str | None = None
    strategy_id: str | None = None
    setup_tag: str | None = None


def extract_trade_records(
    entries: Sequence[JournalEntry | TradeRecord | dict],
) -> tuple[list[TradeRecord], int]:
    """Separate closed trades from open/partial trades.

    Returns:
        (closed_trade_records, open_trades_count)
    """
    closed_records: list[TradeRecord] = []
    open_count = 0

    for item in entries:
        if isinstance(item, TradeRecord):
            if item.status.upper() == "CLOSED" and item.close_time is not None:
                closed_records.append(item)
            else:
                open_count += 1
            continue

        if isinstance(item, dict):
            status = str(item.get("status", "CLOSED")).upper()
            close_time = item.get("close_time")
            if status != "CLOSED" or close_time is None:
                open_count += 1
                continue

            record = TradeRecord(
                id=str(item.get("id", uuid.uuid4())),
                account_id=str(item.get("account_id", "")),
                symbol=str(item.get("symbol", "")).upper(),
                direction=str(item.get("direction", "BUY")).upper(),
                volume=float(item.get("volume", 0.0)),
                entry_price=float(item.get("entry_price", 0.0)),
                exit_price=float(item["exit_price"])
                if item.get("exit_price") is not None
                else None,
                gross_profit=float(item.get("gross_profit", 0.0)),
                commission=float(item.get("commission", 0.0)),
                swap=float(item.get("swap", 0.0)),
                net_pnl=float(item.get("net_pnl", 0.0)),
                open_time=item.get("open_time", datetime.now()),
                close_time=close_time,
                status="CLOSED",
                session=item.get("session"),
                strategy_id=str(item["strategy_id"]) if item.get("strategy_id") else None,
                setup_tag=item.get("setup_tag"),
            )
            closed_records.append(record)
            continue

        # JournalEntry ORM model
        status = str(getattr(item, "status", "CLOSED")).upper()
        close_time = getattr(item, "close_time", None)
        if status != "CLOSED" or close_time is None:
            open_count += 1
            continue

        net_pnl = getattr(item, "net_pnl", 0.0)
        if net_pnl is None:
            net_pnl = 0.0

        record = TradeRecord(
            id=str(getattr(item, "id", uuid.uuid4())),
            account_id=str(getattr(item, "account_id", "")),
            symbol=str(getattr(item, "symbol", "")).upper(),
            direction=str(getattr(item, "direction", "BUY")).upper(),
            volume=float(getattr(item, "volume", 0.0)),
            entry_price=float(getattr(item, "entry_price", 0.0)),
            exit_price=float(item.exit_price)
            if getattr(item, "exit_price", None) is not None
            else None,
            gross_profit=float(getattr(item, "gross_profit", 0.0) or 0.0),
            commission=float(getattr(item, "commission", 0.0) or 0.0),
            swap=float(getattr(item, "swap", 0.0) or 0.0),
            net_pnl=float(net_pnl),
            open_time=getattr(item, "open_time", datetime.now()),
            close_time=close_time,
            status="CLOSED",
            session=getattr(item, "session", None),
            strategy_id=str(item.strategy_id) if getattr(item, "strategy_id", None) else None,
            setup_tag=getattr(item, "setup_tag", None),
        )
        closed_records.append(record)

    return closed_records, open_count


def _sort_trades_chronological(trades: Sequence[TradeRecord]) -> list[TradeRecord]:
    """Sort trades deterministically by close_time ASC, open_time ASC, id ASC."""
    return sorted(trades, key=lambda t: (t.close_time, t.open_time, str(t.id)))


def calculate_sharpe_sortino(
    trades: Sequence[TradeRecord],
    initial_balance: float = 0.0,
    risk_free_rate_annual: float = 0.0,
) -> tuple[float | None, float | None, RatioAssumptions]:
    """Calculate Sharpe and Sortino ratios with explicitly documented assumptions.

    Assumptions:
    1. Return series:
       - If initial_balance > 0: percentage return per trade r_k = net_pnl_k / E_{k-1}.
       - If initial_balance <= 0: monetary net_pnl per trade.
    2. Risk-free rate: defaults to 0.0 per trade period.
    3. Minimum Acceptable Return (MAR) target: 0.0.
    4. Downside deviation: sqrt( (1 / N) * sum( min(r_k - MAR, 0)^2 ) ).
    5. Annualization: trades occur at irregular intraday intervals. Unannualized per-trade
       ratios are returned by default to prevent specious annualization.
    """
    n = len(trades)
    sorted_trades = _sort_trades_chronological(trades)

    if initial_balance > 0:
        return_series_name = "per_trade_net_pnl_pct"
        returns: list[float] = []
        current_eq = initial_balance
        for t in sorted_trades:
            pre_trade_eq = current_eq
            r_k = (t.net_pnl / pre_trade_eq) if pre_trade_eq > 0 else (t.net_pnl / initial_balance)
            returns.append(r_k)
            current_eq += t.net_pnl
        ret_arr = np.array(returns, dtype=np.float64)
    else:
        return_series_name = "per_trade_monetary_pnl"
        ret_arr = np.array([t.net_pnl for t in sorted_trades], dtype=np.float64)

    assumptions = RatioAssumptions(
        return_series=return_series_name,
        risk_free_rate_annual=risk_free_rate_annual,
        risk_free_rate_per_period=0.0,
        downside_deviation_target=0.0,
        is_annualized=False,
        annualization_notes="Unannualized per-trade ratio. Irregular trade frequency; annualization without defensible trade frequency is omitted.",
    )

    if n < 2:
        return None, None, assumptions

    # Sample standard deviation (ddof=1)
    std_dev = float(np.std(ret_arr, ddof=1))
    mean_ret = float(np.mean(ret_arr))

    # Sharpe ratio
    if std_dev <= 1e-12 or math.isnan(std_dev):
        sharpe = None
    else:
        sharpe = round((mean_ret - assumptions.risk_free_rate_per_period) / std_dev, 2)

    # Sortino downside deviation: sqrt( (1/N) * sum(min(r_k, 0)^2) )
    downside_diffs = np.minimum(ret_arr - assumptions.downside_deviation_target, 0.0)
    downside_variance = float(np.mean(downside_diffs**2))
    downside_dev = math.sqrt(downside_variance)

    if downside_dev <= 1e-12 or math.isnan(downside_dev):
        sortino = None
    else:
        sortino = round((mean_ret - assumptions.risk_free_rate_per_period) / downside_dev, 2)

    return sharpe, sortino, assumptions


def calculate_equity_curve(
    trades: Sequence[TradeRecord],
    initial_balance: float = 0.0,
    currency: str = "USD",
    account_id: uuid.UUID | None = None,
) -> EquityCurveResponse:
    """Generate chronological equity curve, high-water mark, and drawdown series."""
    sorted_trades = _sort_trades_chronological(trades)
    points: list[EquityPoint] = []

    current_balance = float(initial_balance)
    current_equity = float(initial_balance)
    cum_pnl = 0.0
    peak_equity = float(initial_balance)
    max_dd_monetary = 0.0
    max_dd_pct = 0.0

    # Baseline origin point (index 0)
    start_ts = sorted_trades[0].open_time if sorted_trades else datetime.now()
    points.append(
        EquityPoint(
            point_index=0,
            timestamp=start_ts,
            trade_id=None,
            balance=round(current_balance, 2),
            equity=round(current_equity, 2),
            cumulative_pnl=0.0,
            peak_equity=round(peak_equity, 2),
            drawdown_monetary=0.0,
            drawdown_percentage=0.0,
        )
    )

    for idx, t in enumerate(sorted_trades, start=1):
        cum_pnl += t.net_pnl
        current_balance += t.net_pnl
        current_equity += t.net_pnl

        if current_equity > peak_equity:
            peak_equity = current_equity

        dd_monetary = max(peak_equity - current_equity, 0.0)
        if dd_monetary > max_dd_monetary:
            max_dd_monetary = dd_monetary

        if peak_equity > 0:
            dd_pct = (dd_monetary / peak_equity) * 100.0
        else:
            dd_pct = 0.0

        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

        points.append(
            EquityPoint(
                point_index=idx,
                timestamp=t.close_time,
                trade_id=t.id,
                balance=round(current_balance, 2),
                equity=round(current_equity, 2),
                cumulative_pnl=round(cum_pnl, 2),
                peak_equity=round(peak_equity, 2),
                drawdown_monetary=round(dd_monetary, 2),
                drawdown_percentage=round(dd_pct, 2),
            )
        )

    return EquityCurveResponse(
        account_id=account_id,
        currency=currency,
        initial_balance=round(initial_balance, 2),
        current_equity=round(current_equity, 2),
        total_net_pnl=round(cum_pnl, 2),
        max_drawdown_monetary=round(max_dd_monetary, 2),
        max_drawdown_percentage=round(max_dd_pct, 2),
        points=points,
    )


def calculate_performance_metrics(
    trades: Sequence[TradeRecord],
    initial_balance: float = 0.0,
    currency: str = "USD",
    open_trades_count: int = 0,
) -> PerformanceMetrics:
    """Calculate deterministic financial performance metrics across closed trades."""
    n = len(trades)

    if n == 0:
        return PerformanceMetrics(
            currency=currency,
            initial_balance=round(initial_balance, 2),
            closed_equity=round(initial_balance, 2),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            open_trades_count=open_trades_count,
            win_rate=0.0,
            loss_rate=0.0,
            breakeven_rate=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            net_pnl=0.0,
            total_commission=0.0,
            total_swap=0.0,
            average_win=0.0,
            average_loss=0.0,
            win_loss_ratio=None,
            profit_factor=None,
            expectancy_per_trade=0.0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            current_streak=0,
            max_drawdown_monetary=0.0,
            max_drawdown_percentage=0.0,
            sharpe_ratio=None,
            sortino_ratio=None,
            ratio_assumptions=RatioAssumptions(),
        )

    sorted_trades = _sort_trades_chronological(trades)

    wins: list[float] = []
    losses: list[float] = []
    be_count = 0
    total_commission = 0.0
    total_swap = 0.0
    total_net_pnl = 0.0

    # Streak counters
    max_wins = 0
    max_losses = 0
    curr_wins = 0
    curr_losses = 0
    streak_history: list[int] = []  # +1 for win, -1 for loss, 0 for BE

    for t in sorted_trades:
        pnl = t.net_pnl
        total_net_pnl += pnl
        total_commission += t.commission
        total_swap += t.swap

        if pnl > 1e-9:
            wins.append(pnl)
            curr_wins += 1
            curr_losses = 0
            if curr_wins > max_wins:
                max_wins = curr_wins
            streak_history.append(+1)
        elif pnl < -1e-9:
            losses.append(abs(pnl))
            curr_losses += 1
            curr_wins = 0
            if curr_losses > max_losses:
                max_losses = curr_losses
            streak_history.append(-1)
        else:
            be_count += 1
            curr_wins = 0
            curr_losses = 0
            streak_history.append(0)

    # Current streak calculation
    current_streak = 0
    if streak_history:
        last_outcome = streak_history[-1]
        if last_outcome != 0:
            count = 0
            for item in reversed(streak_history):
                if item == last_outcome:
                    count += 1
                else:
                    break
            current_streak = count * last_outcome

    n_wins = len(wins)
    n_losses = len(losses)
    win_rate = round((n_wins / n) * 100.0, 2)
    loss_rate = round((n_losses / n) * 100.0, 2)
    be_rate = round((be_count / n) * 100.0, 2)

    gross_profit = float(np.sum(wins)) if n_wins > 0 else 0.0
    gross_loss = float(np.sum(losses)) if n_losses > 0 else 0.0
    net_pnl = float(total_net_pnl)

    avg_win = round(gross_profit / n_wins, 2) if n_wins > 0 else 0.0
    avg_loss = round(gross_loss / n_losses, 2) if n_losses > 0 else 0.0

    win_loss_ratio = round(avg_win / avg_loss, 2) if avg_loss > 0 else None

    # Profit Factor: Gross Profit / Gross Loss (Safe division: None if gross_loss == 0)
    if gross_loss > 1e-9:
        profit_factor = round(gross_profit / gross_loss, 2)
    else:
        profit_factor = None

    expectancy = round(net_pnl / n, 2)

    # Equity curve and maximum drawdown
    eq_response = calculate_equity_curve(
        sorted_trades, initial_balance=initial_balance, currency=currency
    )

    # Sharpe and Sortino
    sharpe, sortino, assumptions = calculate_sharpe_sortino(
        sorted_trades, initial_balance=initial_balance
    )

    return PerformanceMetrics(
        currency=currency,
        initial_balance=round(initial_balance, 2),
        closed_equity=eq_response.current_equity,
        total_trades=n,
        winning_trades=n_wins,
        losing_trades=n_losses,
        breakeven_trades=be_count,
        open_trades_count=open_trades_count,
        win_rate=win_rate,
        loss_rate=loss_rate,
        breakeven_rate=be_rate,
        gross_profit=round(gross_profit, 2),
        gross_loss=round(gross_loss, 2),
        net_pnl=round(net_pnl, 2),
        total_commission=round(total_commission, 2),
        total_swap=round(total_swap, 2),
        average_win=avg_win,
        average_loss=avg_loss,
        win_loss_ratio=win_loss_ratio,
        profit_factor=profit_factor,
        expectancy_per_trade=expectancy,
        max_consecutive_wins=max_wins,
        max_consecutive_losses=max_losses,
        current_streak=current_streak,
        max_drawdown_monetary=eq_response.max_drawdown_monetary,
        max_drawdown_percentage=eq_response.max_drawdown_percentage,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        ratio_assumptions=assumptions,
    )


def calculate_breakdowns(trades: Sequence[TradeRecord]) -> AnalyticsBreakdownsResponse:
    """Calculate multi-dimensional performance breakdowns across categories."""
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def _aggregate_category(grouped: dict[str, list[TradeRecord]]) -> list[CategoryBreakdownItem]:
        items: list[CategoryBreakdownItem] = []
        for cat_label, cat_trades in grouped.items():
            tot = len(cat_trades)
            if tot == 0:
                continue

            wins = [t.net_pnl for t in cat_trades if t.net_pnl > 1e-9]
            losses = [abs(t.net_pnl) for t in cat_trades if t.net_pnl < -1e-9]
            be = [t for t in cat_trades if abs(t.net_pnl) <= 1e-9]

            n_w = len(wins)
            n_l = len(losses)
            gp = float(np.sum(wins)) if n_w > 0 else 0.0
            gl = float(np.sum(losses)) if n_l > 0 else 0.0
            npnl = float(np.sum([t.net_pnl for t in cat_trades]))

            pf = round(gp / gl, 2) if gl > 1e-9 else None

            items.append(
                CategoryBreakdownItem(
                    category=cat_label,
                    total_trades=tot,
                    wins=n_w,
                    losses=n_l,
                    breakevens=len(be),
                    win_rate=round((n_w / tot) * 100.0, 2),
                    gross_profit=round(gp, 2),
                    gross_loss=round(gl, 2),
                    net_pnl=round(npnl, 2),
                    profit_factor=pf,
                    average_trade=round(npnl / tot, 2),
                )
            )
        return items

    by_symbol_map: dict[str, list[TradeRecord]] = {}
    by_direction_map: dict[str, list[TradeRecord]] = {}
    by_session_map: dict[str, list[TradeRecord]] = {}
    by_dow_map: dict[str, list[TradeRecord]] = {day: [] for day in day_names}
    by_hour_map: dict[str, list[TradeRecord]] = {f"{h:02d}:00": [] for h in range(24)}
    by_strat_map: dict[str, list[TradeRecord]] = {}

    for t in trades:
        # Symbol
        by_symbol_map.setdefault(t.symbol or "UNKNOWN", []).append(t)

        # Direction
        by_direction_map.setdefault(t.direction or "UNKNOWN", []).append(t)

        # Session
        by_session_map.setdefault(t.session or "UNASSIGNED", []).append(t)

        # Day of week
        dow = day_names[t.close_time.weekday()]
        by_dow_map[dow].append(t)

        # Hour of day
        hour_label = f"{t.close_time.hour:02d}:00"
        by_hour_map[hour_label].append(t)

        # Strategy / Setup
        tag = t.setup_tag or (f"Strategy:{t.strategy_id[:8]}" if t.strategy_id else "NONE")
        by_strat_map.setdefault(tag, []).append(t)

    by_symbol = sorted(
        _aggregate_category(by_symbol_map), key=lambda x: x.total_trades, reverse=True
    )
    by_direction = sorted(
        _aggregate_category(by_direction_map), key=lambda x: x.total_trades, reverse=True
    )
    by_session = sorted(
        _aggregate_category(by_session_map), key=lambda x: x.total_trades, reverse=True
    )
    by_dow = [item for item in _aggregate_category(by_dow_map) if item.total_trades > 0]
    by_hour = [item for item in _aggregate_category(by_hour_map) if item.total_trades > 0]
    by_strat = sorted(_aggregate_category(by_strat_map), key=lambda x: x.total_trades, reverse=True)

    return AnalyticsBreakdownsResponse(
        by_symbol=by_symbol,
        by_direction=by_direction,
        by_session=by_session,
        by_day_of_week=by_dow,
        by_hour_of_day=by_hour,
        by_strategy=by_strat,
    )
