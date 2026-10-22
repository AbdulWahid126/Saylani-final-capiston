"""Authenticated API endpoints for Trading Behavior Analyzer and discipline evaluation."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.behavior_analyzer import analyze_trading_behavior
from app.api.deps import enforce_resource_ownership, get_current_user
from app.core.errors import BadRequestError, NotFoundError
from app.db.session import get_db
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.rule import UserRule
from app.models.user import User
from app.schemas.behavior import (
    BehaviorAnalysisConfig,
    BehaviorAnalyzeRequest,
    BehaviorFinding,
    BehaviorFindingsResponse,
    BehaviorPatternType,
    BehaviorSeverity,
    BehaviorSummaryResponse,
    BehaviorUserConfigRequest,
    BehaviorUserConfigResponse,
)
from app.schemas.common import DataClassificationBadge

router = APIRouter(tags=["Trading Behavior"])

BEHAVIOR_RULE_TYPE = "BEHAVIOR_CONFIG"
BEHAVIOR_RULE_NAME = "Default Behavioral Analysis Configuration"


async def _get_user_behavior_config(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> tuple[BehaviorAnalysisConfig, UserRule | None]:
    """Retrieve user's saved behavioral configuration or return standard defaults."""
    stmt = select(UserRule).where(
        UserRule.user_id == user_id,
        UserRule.rule_type == BEHAVIOR_RULE_TYPE,
        UserRule.is_active.is_(True),
    )
    rule = await db.scalar(stmt)
    if not rule or not rule.parameters:
        return BehaviorAnalysisConfig(), None

    try:
        config = BehaviorAnalysisConfig(**rule.parameters)
        return config, rule
    except Exception:
        return BehaviorAnalysisConfig(), rule


async def _fetch_scoped_journal_entries(
    db: AsyncSession,
    current_user: User,
    account_id: uuid.UUID | None,
    from_date: datetime | None,
    to_date: datetime | None,
    symbol: str | None,
) -> list[JournalEntry]:
    """Fetch journal entries scoped to authenticated user and optional filters."""
    if from_date and to_date and from_date > to_date:
        raise BadRequestError("from_date cannot be greater than to_date")

    if account_id is not None:
        account_stmt = select(TradingAccount).where(TradingAccount.id == account_id)
        account = await db.scalar(account_stmt)
        if not account:
            raise NotFoundError("TradingAccount", account_id)
        enforce_resource_ownership(account.user_id, current_user)
        allowed_account_ids = [account.id]
    else:
        user_accounts_stmt = select(TradingAccount.id).where(
            TradingAccount.user_id == current_user.id
        )
        accounts_res = await db.scalars(user_accounts_stmt)
        allowed_account_ids = list(accounts_res.all())
        if not allowed_account_ids:
            return []

    query = select(JournalEntry).where(
        JournalEntry.user_id == current_user.id,
        JournalEntry.account_id.in_(allowed_account_ids),
    )

    if symbol:
        query = query.where(JournalEntry.symbol == symbol.strip().upper())

    if from_date:
        query = query.where(
            (JournalEntry.open_time >= from_date) | (JournalEntry.close_time >= from_date)
        )
    if to_date:
        query = query.where(
            (JournalEntry.open_time <= to_date) | (JournalEntry.close_time <= to_date)
        )

    query = query.order_by(
        JournalEntry.close_time.asc(),
        JournalEntry.open_time.asc(),
        JournalEntry.id.asc(),
    )

    res = await db.scalars(query)
    return list(res.all())


# ==============================================================================
# INTERNAL COMPUTATION HELPERS
# ==============================================================================


async def _compute_behavior_summary(
    db: AsyncSession,
    current_user: User,
    account_id: uuid.UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    symbol: str | None = None,
    reentry_window_minutes: int | None = None,
    max_trades_per_day: int | None = None,
    max_trades_per_session: int | None = None,
    size_escalation_ratio: float | None = None,
    session_timezone: str | None = None,
) -> BehaviorSummaryResponse:
    """Internal helper to compute behavior summary without FastAPI Query defaults."""
    config, _ = await _get_user_behavior_config(db, current_user.id)

    config_dict = config.model_dump()
    if reentry_window_minutes is not None:
        config_dict["reentry_window_minutes"] = reentry_window_minutes
    if max_trades_per_day is not None:
        config_dict["max_trades_per_day"] = max_trades_per_day
    if max_trades_per_session is not None:
        config_dict["max_trades_per_session"] = max_trades_per_session
    if size_escalation_ratio is not None:
        config_dict["size_escalation_ratio"] = size_escalation_ratio
    if session_timezone is not None:
        config_dict["session_timezone"] = session_timezone

    effective_config = BehaviorAnalysisConfig(**config_dict)

    entries = await _fetch_scoped_journal_entries(
        db=db,
        current_user=current_user,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
    )

    return analyze_trading_behavior(
        entries=entries,
        config=effective_config,
        account_id=account_id,
    )


async def _compute_behavior_findings(
    db: AsyncSession,
    current_user: User,
    account_id: uuid.UUID | None = None,
    pattern_type: BehaviorPatternType | None = None,
    severity: BehaviorSeverity | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    symbol: str | None = None,
) -> BehaviorFindingsResponse:
    """Internal helper to compute filtered behavior findings without FastAPI Query defaults."""
    config, _ = await _get_user_behavior_config(db, current_user.id)

    entries = await _fetch_scoped_journal_entries(
        db=db,
        current_user=current_user,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
    )

    summary = analyze_trading_behavior(
        entries=entries,
        config=config,
        account_id=account_id,
    )

    findings: list[BehaviorFinding] = summary.findings
    if pattern_type is not None:
        findings = [f for f in findings if f.pattern_type == pattern_type]
    if severity is not None:
        findings = [f for f in findings if f.severity == severity]

    return BehaviorFindingsResponse(
        total_findings=len(findings),
        findings=findings,
        data_badge=DataClassificationBadge.HISTORICAL_STATISTICS,
    )


# ==============================================================================
# BEHAVIOR SUMMARY & FINDINGS ENDPOINTS
# ==============================================================================


@router.get("/behavior/summary", response_model=BehaviorSummaryResponse)
async def get_behavior_summary(
    account_id: uuid.UUID | None = Query(
        default=None, description="Scope analysis to a specific trading account."
    ),
    from_date: datetime | None = Query(default=None, description="Start date filter (inclusive)."),
    to_date: datetime | None = Query(default=None, description="End date filter (inclusive)."),
    symbol: str | None = Query(default=None, description="Symbol filter (e.g. EURUSD)."),
    reentry_window_minutes: int | None = Query(
        default=None, ge=1, le=1440, description="Override re-entry window in minutes."
    ),
    max_trades_per_day: int | None = Query(
        default=None, ge=1, le=1000, description="Override max daily trades threshold."
    ),
    max_trades_per_session: int | None = Query(
        default=None, ge=1, le=500, description="Override max session trades threshold."
    ),
    size_escalation_ratio: float | None = Query(
        default=None, ge=1.01, le=20.0, description="Override size escalation multiplier."
    ),
    session_timezone: str | None = Query(
        default=None, description="Override session timezone (e.g. 'America/New_York')."
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorSummaryResponse:
    """Retrieve comprehensive deterministic behavioral pattern analysis and discipline score."""
    return await _compute_behavior_summary(
        db=db,
        current_user=current_user,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
        reentry_window_minutes=reentry_window_minutes,
        max_trades_per_day=max_trades_per_day,
        max_trades_per_session=max_trades_per_session,
        size_escalation_ratio=size_escalation_ratio,
        session_timezone=session_timezone,
    )


@router.get("/behavior/findings", response_model=BehaviorFindingsResponse)
async def get_behavior_findings(
    account_id: uuid.UUID | None = Query(
        default=None, description="Scope findings to a specific trading account."
    ),
    pattern_type: BehaviorPatternType | None = Query(
        default=None, description="Filter by behavioral pattern type."
    ),
    severity: BehaviorSeverity | None = Query(
        default=None, description="Filter by severity level (LOW, MEDIUM, HIGH)."
    ),
    from_date: datetime | None = Query(default=None, description="Start date filter (inclusive)."),
    to_date: datetime | None = Query(default=None, description="End date filter (inclusive)."),
    symbol: str | None = Query(default=None, description="Symbol filter (e.g. EURUSD)."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorFindingsResponse:
    """Retrieve filtered detailed behavioral findings with evidence."""
    return await _compute_behavior_findings(
        db=db,
        current_user=current_user,
        account_id=account_id,
        pattern_type=pattern_type,
        severity=severity,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
    )


@router.post("/behavior/analyze", response_model=BehaviorSummaryResponse)
async def analyze_behavior_on_demand(
    payload: BehaviorAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorSummaryResponse:
    """Execute on-demand behavioral pattern analysis with custom parameters."""
    entries = await _fetch_scoped_journal_entries(
        db=db,
        current_user=current_user,
        account_id=payload.account_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
        symbol=payload.symbol,
    )

    return analyze_trading_behavior(
        entries=entries,
        config=payload.config,
        account_id=payload.account_id,
    )


# ==============================================================================
# ACCOUNT-SCOPED SHORTCUT ROUTES
# ==============================================================================


@router.get(
    "/accounts/{account_id}/behavior/summary",
    response_model=BehaviorSummaryResponse,
)
async def get_account_behavior_summary(
    account_id: uuid.UUID,
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    symbol: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorSummaryResponse:
    """Shortcut endpoint to retrieve behavioral summary for a specific account."""
    return await _compute_behavior_summary(
        db=db,
        current_user=current_user,
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
    )


@router.get(
    "/accounts/{account_id}/behavior/findings",
    response_model=BehaviorFindingsResponse,
)
async def get_account_behavior_findings(
    account_id: uuid.UUID,
    pattern_type: BehaviorPatternType | None = Query(default=None),
    severity: BehaviorSeverity | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    symbol: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorFindingsResponse:
    """Shortcut endpoint to retrieve behavioral findings for a specific account."""
    return await _compute_behavior_findings(
        db=db,
        current_user=current_user,
        account_id=account_id,
        pattern_type=pattern_type,
        severity=severity,
        from_date=from_date,
        to_date=to_date,
        symbol=symbol,
    )


# ==============================================================================

# USER BEHAVIORAL CONFIGURATION MANAGEMENT
# ==============================================================================


@router.get("/behavior/config", response_model=BehaviorUserConfigResponse)
async def get_user_behavior_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorUserConfigResponse:
    """Retrieve the user's saved behavioral configuration or default configuration."""
    config, rule = await _get_user_behavior_config(db, current_user.id)
    return BehaviorUserConfigResponse(
        id=str(rule.id) if rule else "default",
        user_id=str(current_user.id),
        rule_name=rule.rule_name if rule else BEHAVIOR_RULE_NAME,
        config=config,
        is_active=rule.is_active if rule else True,
        updated_at=rule.updated_at if rule else None,
    )


@router.put("/behavior/config", response_model=BehaviorUserConfigResponse)
async def update_user_behavior_config(
    payload: BehaviorUserConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorUserConfigResponse:
    """Save or update user's behavioral configuration preferences."""
    stmt = select(UserRule).where(
        UserRule.user_id == current_user.id,
        UserRule.rule_type == BEHAVIOR_RULE_TYPE,
    )
    rule = await db.scalar(stmt)

    if not rule:
        rule = UserRule(
            id=uuid.uuid4(),
            user_id=current_user.id,
            rule_name=BEHAVIOR_RULE_NAME,
            rule_type=BEHAVIOR_RULE_TYPE,
            parameters=payload.config.model_dump(),
            is_active=True,
        )
        db.add(rule)
    else:
        rule.parameters = payload.config.model_dump()
        rule.is_active = True

    await db.commit()
    await db.refresh(rule)

    return BehaviorUserConfigResponse(
        id=str(rule.id),
        user_id=str(rule.user_id),
        rule_name=rule.rule_name,
        config=BehaviorAnalysisConfig(**rule.parameters),
        is_active=rule.is_active,
        updated_at=rule.updated_at,
    )
