"""Deterministic Prop Firm Risk Manager Engine.

Calculates real-time daily drawdown, static/trailing maximum drawdown,
risk limit utilization percentages, and Green/Amber/Red/Breached status gauges.

ZERO LLM ARITHMETIC: All calculations execute in pure deterministic Python.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.analytics.engine import TradeRecord, _sort_trades_chronological
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.schemas.risk import (
    AccountRiskEvaluationResponse,
    DailyLossCalculationBasis,
    DailyRiskStatus,
    DrawdownModel,
    OverallRiskStatus,
    ProfitTargetStatus,
    PropRiskProfileBase,
    PropRiskProfileResponse,
    RiskSnapshotOverride,
    RiskStatusLevel,
)

# ==============================================================================
# BUILT-IN EXAMPLE PROFILES (Clearly labeled as examples / templates)
# ==============================================================================

TEMPLATE_2STEP_100K = PropRiskProfileResponse(
    id="template-2step-100k",
    name="Template: 2-Step Evaluation 100k (Example)",
    description="Standard 2-step evaluation model: 5% daily loss limit (equity-based), 10% static max loss, 10% profit target.",
    initial_balance=100000.0,
    daily_loss_limit_pct=5.0,
    max_total_loss_limit_pct=10.0,
    drawdown_model=DrawdownModel.STATIC,
    daily_loss_basis=DailyLossCalculationBasis.EQUITY_BASED,
    trail_locks_at_initial_balance=True,
    daily_reset_timezone="Europe/Prague",  # CE(S)T used by European prop firms
    daily_reset_time="00:00:00",
    profit_target_pct=10.0,
    is_template=True,
    user_id=None,
)

TEMPLATE_1STEP_TRAILING_50K = PropRiskProfileResponse(
    id="template-1step-trailing-50k",
    name="Template: 1-Step Trailing 50k (Example)",
    description="1-step challenge model: 4% daily loss limit, 6% trailing max drawdown with lock at initial balance, 8% profit target.",
    initial_balance=50000.0,
    daily_loss_limit_pct=4.0,
    max_total_loss_limit_pct=6.0,
    drawdown_model=DrawdownModel.TRAILING,
    daily_loss_basis=DailyLossCalculationBasis.EQUITY_BASED,
    trail_locks_at_initial_balance=True,
    daily_reset_timezone="UTC",
    daily_reset_time="00:00:00",
    profit_target_pct=8.0,
    is_template=True,
    user_id=None,
)

TEMPLATE_STATIC_10K = PropRiskProfileResponse(
    id="template-static-10k",
    name="Template: Static 10k Challenge (Example)",
    description="10k evaluation challenge: 5% balance-based daily loss limit, 10% static max loss, NY 17:00 rollover reset.",
    initial_balance=10000.0,
    daily_loss_limit_pct=5.0,
    max_total_loss_limit_pct=10.0,
    drawdown_model=DrawdownModel.STATIC,
    daily_loss_basis=DailyLossCalculationBasis.BALANCE_BASED,
    trail_locks_at_initial_balance=False,
    daily_reset_timezone="America/New_York",
    daily_reset_time="17:00:00",
    profit_target_pct=10.0,
    is_template=True,
    user_id=None,
)

BUILTIN_TEMPLATES: list[PropRiskProfileResponse] = [
    TEMPLATE_2STEP_100K,
    TEMPLATE_1STEP_TRAILING_50K,
    TEMPLATE_STATIC_10K,
]


def get_builtin_template(template_id: str) -> PropRiskProfileResponse | None:
    """Find a built-in template profile by its slug identifier."""
    for t in BUILTIN_TEMPLATES:
        if str(t.id) == template_id:
            return t
    return None


# ==============================================================================
# TIMEZONE & SESSION RESET UTILITIES
# ==============================================================================


def get_daily_reset_window(
    timezone_name: str,
    reset_time_str: str = "00:00:00",
    current_time: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Calculate the UTC start and end bounds of the current trading day.

    Accounts for the configured timezone and Daylight Saving Time (DST) transitions.
    Returns: (session_start_utc, session_end_utc)
    """
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        try:
            tz = ZoneInfo("UTC")
        except Exception:
            tz = UTC

    # Parse HH:MM:SS
    try:
        parts = [int(p) for p in reset_time_str.split(":")]
        r_hour = parts[0]
        r_min = parts[1] if len(parts) > 1 else 0
        r_sec = parts[2] if len(parts) > 2 else 0
        reset_t = time(hour=r_hour, minute=r_min, second=r_sec)
    except Exception:
        reset_t = time(0, 0, 0)

    now_utc = current_time if current_time is not None else datetime.now(UTC)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=UTC)

    # Convert to configured local timezone
    now_in_tz = now_utc.astimezone(tz)
    today_reset = datetime.combine(now_in_tz.date(), reset_t, tzinfo=tz)

    if now_in_tz >= today_reset:
        start_tz = today_reset
        end_tz = datetime.combine(now_in_tz.date() + timedelta(days=1), reset_t, tzinfo=tz)
    else:
        start_tz = datetime.combine(now_in_tz.date() - timedelta(days=1), reset_t, tzinfo=tz)
        end_tz = today_reset

    start_utc = start_tz.astimezone(UTC)
    end_utc = end_tz.astimezone(UTC)
    return start_utc, end_utc


# ==============================================================================
# RISK EVALUATION CORE
# ==============================================================================


def evaluate_account_risk(
    account: TradingAccount,
    profile: PropRiskProfileBase | PropRiskProfileResponse,
    closed_trades: Sequence[TradeRecord | JournalEntry],
    open_trades: Sequence[JournalEntry | dict] | None = None,
    snapshot_override: RiskSnapshotOverride | None = None,
    evaluation_time: datetime | None = None,
    profile_id: uuid.UUID | str | None = None,
) -> AccountRiskEvaluationResponse:
    """Evaluate prop firm risk limits, drawdowns, and status for a trading account."""
    eval_time = evaluation_time if evaluation_time is not None else datetime.now(UTC)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=UTC)

    # 1. Resolve effective balance, equity, and floating P&L
    is_live_sync = snapshot_override is None
    cur_balance = float(account.balance or 0.0)
    cur_equity = float(account.equity or 0.0)
    cur_floating_pnl = cur_equity - cur_balance

    if snapshot_override is not None:
        if snapshot_override.current_balance is not None:
            cur_balance = float(snapshot_override.current_balance)
        if snapshot_override.current_equity is not None:
            cur_equity = float(snapshot_override.current_equity)
        if snapshot_override.current_floating_pnl is not None:
            cur_floating_pnl = float(snapshot_override.current_floating_pnl)
        elif (
            snapshot_override.current_equity is not None
            and snapshot_override.current_balance is not None
        ):
            cur_floating_pnl = cur_equity - cur_balance

    # Validate critical data presence
    if cur_balance <= 0.0 and profile.initial_balance > 0.0:
        # Fallback to initial balance if account balance not yet populated
        cur_balance = profile.initial_balance
        cur_equity = cur_balance + cur_floating_pnl

    is_data_available = cur_balance > 0.0 and cur_equity > 0.0
    data_notes = None if is_data_available else "Account balance or equity is zero or unavailable."

    # 2. Daily Reset Window and Partitioning
    session_start_utc, session_end_utc = get_daily_reset_window(
        timezone_name=profile.daily_reset_timezone,
        reset_time_str=profile.daily_reset_time,
        current_time=eval_time,
    )

    # Calculate net P&L of trades closed in the current daily session
    daily_closed_pnl = 0.0
    for t in closed_trades:
        c_time = getattr(t, "close_time", None)
        if c_time is not None:
            if c_time.tzinfo is None:
                c_time = c_time.replace(tzinfo=UTC)
            if c_time >= session_start_utc:
                pnl = getattr(t, "net_pnl", 0.0) or 0.0
                daily_closed_pnl += float(pnl)

    # Start-of-day balance = current balance minus P&L realized today
    start_of_day_balance = cur_balance - daily_closed_pnl

    # 3. Daily Loss Limit Calculations
    ref_balance = profile.initial_balance
    daily_limit_amt = round(ref_balance * (profile.daily_loss_limit_pct / 100.0), 2)

    if profile.daily_loss_basis == DailyLossCalculationBasis.EQUITY_BASED:
        effective_daily_loss = max(0.0, -(daily_closed_pnl + cur_floating_pnl))
    else:  # BALANCE_BASED
        effective_daily_loss = max(0.0, -daily_closed_pnl)

    daily_loss_remaining = max(0.0, daily_limit_amt - effective_daily_loss)
    daily_utilization = (
        (effective_daily_loss / daily_limit_amt * 100.0) if daily_limit_amt > 0 else 0.0
    )

    # Daily Status Level
    if daily_utilization >= 100.0:
        daily_status = RiskStatusLevel.BREACHED
        daily_breached = True
        daily_explanation = f"Daily loss limit breached! Incurred ${effective_daily_loss:,.2f} loss vs ${daily_limit_amt:,.2f} limit."
    elif daily_utilization >= 80.0:
        daily_status = RiskStatusLevel.RED
        daily_breached = False
        daily_explanation = f"High Risk: Daily loss is at {daily_utilization:.1f}% of limit (${daily_loss_remaining:,.2f} remaining)."
    elif daily_utilization >= 50.0:
        daily_status = RiskStatusLevel.AMBER
        daily_breached = False
        daily_explanation = f"Caution: Daily loss is at {daily_utilization:.1f}% of limit (${daily_loss_remaining:,.2f} remaining)."
    else:
        daily_status = RiskStatusLevel.GREEN
        daily_breached = False
        daily_explanation = f"Safe: Daily risk utilization is {daily_utilization:.1f}% (${daily_loss_remaining:,.2f} remaining)."

    # 4. Overall / Trailing Drawdown Limit Calculations
    overall_limit_amt = round(ref_balance * (profile.max_total_loss_limit_pct / 100.0), 2)

    # Determine peak high-water mark across history and current state
    peak_hwm = max(ref_balance, cur_balance, cur_equity)
    if closed_trades:
        # Check closed equity progression
        cum = 0.0
        for t in _sort_trades_chronological(
            [
                t
                for t in closed_trades
                if hasattr(t, "id") and hasattr(t, "close_time") and t.close_time is not None
            ]
        ):
            cum += float(t.net_pnl or 0.0)
            pt_eq = ref_balance + cum
            if pt_eq > peak_hwm:
                peak_hwm = pt_eq

    if profile.drawdown_model == DrawdownModel.STATIC:
        hard_floor = round(ref_balance - overall_limit_amt, 2)
        overall_loss_current = max(0.0, ref_balance - cur_equity)
        overall_loss_remaining = max(0.0, cur_equity - hard_floor)
        overall_utilization = (
            (overall_loss_current / overall_limit_amt * 100.0) if overall_limit_amt > 0 else 0.0
        )
    else:  # TRAILING
        trailing_floor = peak_hwm - overall_limit_amt
        if profile.trail_locks_at_initial_balance and trailing_floor > ref_balance:
            hard_floor = round(ref_balance, 2)
        else:
            hard_floor = round(trailing_floor, 2)

        overall_loss_current = max(0.0, peak_hwm - cur_equity)
        overall_loss_remaining = max(0.0, cur_equity - hard_floor)
        max_allowable_drop = peak_hwm - hard_floor
        overall_utilization = (
            (overall_loss_current / max_allowable_drop * 100.0) if max_allowable_drop > 0 else 0.0
        )

    # Overall Status Level
    if overall_utilization >= 100.0 or cur_equity <= hard_floor:
        overall_status = RiskStatusLevel.BREACHED
        overall_breached = True
        overall_explanation = f"Maximum overall loss limit breached! Equity dropped below floor level of ${hard_floor:,.2f}."
    elif overall_utilization >= 80.0:
        overall_status = RiskStatusLevel.RED
        overall_breached = False
        overall_explanation = f"High Risk: Overall drawdown is at {overall_utilization:.1f}% of limit (${overall_loss_remaining:,.2f} buffer to floor)."
    elif overall_utilization >= 50.0:
        overall_status = RiskStatusLevel.AMBER
        overall_breached = False
        overall_explanation = f"Caution: Overall drawdown is at {overall_utilization:.1f}% of limit (${overall_loss_remaining:,.2f} buffer to floor)."
    else:
        overall_status = RiskStatusLevel.GREEN
        overall_breached = False
        overall_explanation = f"Safe: Overall loss utilization is {overall_utilization:.1f}% (${overall_loss_remaining:,.2f} buffer to floor)."

    # 5. Profit Target (Optional Challenge Goal)
    target_status = None
    if profile.profit_target_pct is not None and profile.profit_target_pct > 0.0:
        target_amt = round(ref_balance * (profile.profit_target_pct / 100.0), 2)
        cur_profit = round(cur_equity - ref_balance, 2)
        rem_profit = max(0.0, target_amt - cur_profit)
        progress_pct = (
            min(100.0, max(0.0, (cur_profit / target_amt * 100.0))) if target_amt > 0 else 0.0
        )
        achieved = cur_profit >= target_amt
        target_status = ProfitTargetStatus(
            target_amount=target_amt,
            current_profit=cur_profit,
            remaining_profit_required=round(rem_profit, 2),
            progress_percentage=round(progress_pct, 2),
            target_achieved=achieved,
        )

    # 6. Overall Composite Status Level
    if not is_data_available:
        composite_status = RiskStatusLevel.UNAVAILABLE
        summary_msg = "Risk evaluation unavailable: account balance or equity cannot be determined."
    elif daily_breached or overall_breached:
        composite_status = RiskStatusLevel.BREACHED
        summary_msg = "CRITICAL: Account has breached prop firm challenge risk limits."
    elif daily_status == RiskStatusLevel.RED or overall_status == RiskStatusLevel.RED:
        composite_status = RiskStatusLevel.RED
        summary_msg = "WARNING: Account is in RED risk zone (>80% limit consumed). Immediate risk reduction advised."
    elif daily_status == RiskStatusLevel.AMBER or overall_status == RiskStatusLevel.AMBER:
        composite_status = RiskStatusLevel.AMBER
        summary_msg = "CAUTION: Account is in AMBER risk zone (50-80% limit consumed). Monitor open positions closely."
    else:
        composite_status = RiskStatusLevel.GREEN
        summary_msg = "NORMAL: Account is in GREEN safe risk zone (<50% risk limit consumed)."

    resolved_profile_id = profile_id or getattr(profile, "id", "custom-profile")

    return AccountRiskEvaluationResponse(
        account_id=account.id,
        account_number=account.account_number,
        broker_name=account.broker_name,
        currency=account.currency or "USD",
        profile_id=resolved_profile_id,
        profile_name=profile.name,
        is_live_sync_active=is_live_sync,
        evaluated_at=eval_time,
        is_data_available=is_data_available,
        data_availability_notes=data_notes,
        overall_status_level=composite_status,
        is_any_limit_breached=(daily_breached or overall_breached),
        summary_warning_message=summary_msg,
        daily_risk=DailyRiskStatus(
            start_of_day_balance=round(start_of_day_balance, 2),
            daily_closed_pnl=round(daily_closed_pnl, 2),
            current_floating_pnl=round(cur_floating_pnl, 2),
            effective_daily_loss=round(effective_daily_loss, 2),
            daily_loss_limit_amount=round(daily_limit_amt, 2),
            daily_loss_remaining=round(daily_loss_remaining, 2),
            daily_loss_utilization_pct=round(daily_utilization, 2),
            status_level=daily_status,
            reset_timestamp_utc=session_start_utc,
            next_reset_timestamp_utc=session_end_utc,
            is_breached=daily_breached,
            explanation=daily_explanation,
        ),
        overall_risk=OverallRiskStatus(
            initial_reference_balance=round(ref_balance, 2),
            peak_high_water_mark=round(peak_hwm, 2),
            current_equity=round(cur_equity, 2),
            hard_floor_level=round(hard_floor, 2),
            overall_loss_limit_amount=round(overall_limit_amt, 2),
            overall_loss_current=round(overall_loss_current, 2),
            overall_loss_remaining=round(overall_loss_remaining, 2),
            overall_loss_utilization_pct=round(overall_utilization, 2),
            drawdown_model_used=profile.drawdown_model,
            status_level=overall_status,
            is_breached=overall_breached,
            explanation=overall_explanation,
        ),
        profit_target=target_status,
    )
