"""Authenticated API endpoints for deterministic financial analytics and performance reporting."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.engine import (
    calculate_breakdowns,
    calculate_equity_curve,
    calculate_performance_metrics,
    extract_trade_records,
)
from app.api.deps import enforce_resource_ownership, get_current_user
from app.core.errors import BadRequestError, NotFoundError
from app.db.session import get_db
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsBreakdownsResponse,
    AnalyticsSummaryResponse,
    EquityCurveResponse,
)

router = APIRouter(tags=["Analytics"])


async def _resolve_scope_and_fetch_entries(
    db: AsyncSession,
    current_user: User,
    account_id: uuid.UUID | None,
    from_date: datetime | None,
    to_date: datetime | None,
    symbol: str | None,
    strategy_id: uuid.UUID | None,
    currency_filter: str | None,
) -> tuple[list[JournalEntry], float, str, TradingAccount | None]:
    """Resolves account/currency scope, enforces tenant isolation, and fetches journal entries."""
    if from_date and to_date and from_date > to_date:
        raise BadRequestError("from_date cannot be greater than to_date")

    target_account: TradingAccount | None = None
    initial_balance = 0.0
    currency = "USD"

    if account_id is not None:
        account_stmt = select(TradingAccount).where(TradingAccount.id == account_id)
        target_account = await db.scalar(account_stmt)
        if not target_account:
            raise NotFoundError("TradingAccount", account_id)
        enforce_resource_ownership(target_account.user_id, current_user)

        initial_balance = float(target_account.initial_balance or 0.0)
        currency = target_account.currency or "USD"
        allowed_account_ids = [target_account.id]
    else:
        # Fetch all trading accounts owned by current user
        user_accounts_stmt = select(TradingAccount).where(TradingAccount.user_id == current_user.id)
        accounts_res = await db.scalars(user_accounts_stmt)
        all_accounts = list(accounts_res.all())

        if not all_accounts:
            return [], 0.0, "USD", None

        # Filter accounts by currency if requested
        if currency_filter:
            norm_curr = currency_filter.strip().upper()
            filtered_accounts = [
                acc for acc in all_accounts if (acc.currency or "USD").upper() == norm_curr
            ]
            if not filtered_accounts:
                return [], 0.0, norm_curr, None
            allowed_account_ids = [acc.id for acc in filtered_accounts]
            currency = norm_curr
            initial_balance = sum(float(acc.initial_balance or 0.0) for acc in filtered_accounts)
        else:
            # Check distinct currencies across user accounts
            currencies = {(acc.currency or "USD").upper() for acc in all_accounts}
            if len(currencies) > 1:
                # Disallow mixing currencies without explicit account or currency filter
                sorted_currs = sorted(currencies)
                raise BadRequestError(
                    f"Cannot aggregate across accounts with mixed currencies ({sorted_currs}). "
                    "Please specify an account_id or currency filter."
                )
            currency = next(iter(currencies)) if currencies else "USD"
            allowed_account_ids = [acc.id for acc in all_accounts]
            initial_balance = sum(float(acc.initial_balance or 0.0) for acc in all_accounts)

    # Build query for journal entries
    query = select(JournalEntry).where(
        JournalEntry.user_id == current_user.id,
        JournalEntry.account_id.in_(allowed_account_ids),
    )

    if symbol:
        query = query.where(JournalEntry.symbol == symbol.strip().upper())
    if strategy_id:
        query = query.where(JournalEntry.strategy_id == strategy_id)

    # Date filters apply to trade close_time, but we also include open trades (close_time is None)
    # so that open_trades_count remains accurate.
    if from_date:
        query = query.where(
            (JournalEntry.close_time >= from_date) | (JournalEntry.close_time.is_(None))
        )
    if to_date:
        query = query.where(
            (JournalEntry.close_time <= to_date) | (JournalEntry.close_time.is_(None))
        )

    query = query.order_by(
        JournalEntry.close_time.asc(), JournalEntry.open_time.asc(), JournalEntry.id.asc()
    )

    res = await db.scalars(query)
    entries = list(res.all())
    return entries, initial_balance, currency, target_account


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    account_id: uuid.UUID | None = Query(
        default=None, description="Scope to a specific trading account."
    ),
    from_date: datetime | None = Query(default=None, description="Start date filter (inclusive)."),
    to_date: datetime | None = Query(default=None, description="End date filter (inclusive)."),
    symbol: str | None = Query(default=None, description="Symbol filter (e.g. EURUSD)."),
    strategy_id: uuid.UUID | None = Query(default=None, description="Strategy UUID filter."),
    currency: str | None = Query(default=None, description="Currency filter (e.g. USD)."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryResponse:
    """Retrieve comprehensive deterministic financial performance metrics summary."""
    entries, initial_balance, base_curr, target_account = await _resolve_scope_and_fetch_entries(
        db=db,
        current_user=current_user,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
        strategy_id=strategy_id,
        currency_filter=currency,
    )

    closed_records, open_count = extract_trade_records(entries)
    metrics = calculate_performance_metrics(
        trades=closed_records,
        initial_balance=initial_balance,
        currency=base_curr,
        open_trades_count=open_count,
    )

    return AnalyticsSummaryResponse(
        account_id=target_account.id if target_account else None,
        account_number=target_account.account_number if target_account else None,
        broker_name=target_account.broker_name if target_account else None,
        from_date=from_date,
        to_date=to_date,
        metrics=metrics,
    )


@router.get("/analytics/equity-curve", response_model=EquityCurveResponse)
async def get_analytics_equity_curve(
    account_id: uuid.UUID | None = Query(
        default=None, description="Scope to a specific trading account."
    ),
    from_date: datetime | None = Query(default=None, description="Start date filter (inclusive)."),
    to_date: datetime | None = Query(default=None, description="End date filter (inclusive)."),
    symbol: str | None = Query(default=None, description="Symbol filter (e.g. EURUSD)."),
    strategy_id: uuid.UUID | None = Query(default=None, description="Strategy UUID filter."),
    currency: str | None = Query(default=None, description="Currency filter (e.g. USD)."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EquityCurveResponse:
    """Retrieve chronological equity curve, high-water mark, and drawdown data points."""
    entries, initial_balance, base_curr, target_account = await _resolve_scope_and_fetch_entries(
        db=db,
        current_user=current_user,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
        strategy_id=strategy_id,
        currency_filter=currency,
    )

    closed_records, _ = extract_trade_records(entries)
    return calculate_equity_curve(
        trades=closed_records,
        initial_balance=initial_balance,
        currency=base_curr,
        account_id=target_account.id if target_account else None,
    )


@router.get("/analytics/breakdowns", response_model=AnalyticsBreakdownsResponse)
async def get_analytics_breakdowns(
    account_id: uuid.UUID | None = Query(
        default=None, description="Scope to a specific trading account."
    ),
    from_date: datetime | None = Query(default=None, description="Start date filter (inclusive)."),
    to_date: datetime | None = Query(default=None, description="End date filter (inclusive)."),
    symbol: str | None = Query(default=None, description="Symbol filter (e.g. EURUSD)."),
    strategy_id: uuid.UUID | None = Query(default=None, description="Strategy UUID filter."),
    currency: str | None = Query(default=None, description="Currency filter (e.g. USD)."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsBreakdownsResponse:
    """Retrieve performance breakdowns by symbol, direction, session, day of week, hour, and strategy."""
    entries, _, _, _ = await _resolve_scope_and_fetch_entries(
        db=db,
        current_user=current_user,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
        strategy_id=strategy_id,
        currency_filter=currency,
    )

    closed_records, _ = extract_trade_records(entries)
    return calculate_breakdowns(trades=closed_records)


# Account-specific shortcut endpoints
@router.get("/accounts/{account_id}/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_account_analytics_summary(
    account_id: uuid.UUID,
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    symbol: str | None = Query(default=None),
    strategy_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryResponse:
    """Account-scoped shortcut for retrieving analytics performance summary."""
    return await get_analytics_summary(
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
        strategy_id=strategy_id,
        currency=None,
        current_user=current_user,
        db=db,
    )


@router.get("/accounts/{account_id}/analytics/equity-curve", response_model=EquityCurveResponse)
async def get_account_equity_curve(
    account_id: uuid.UUID,
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    symbol: str | None = Query(default=None),
    strategy_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EquityCurveResponse:
    """Account-scoped shortcut for retrieving equity curve."""
    return await get_analytics_equity_curve(
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
        strategy_id=strategy_id,
        currency=None,
        current_user=current_user,
        db=db,
    )
