"""Authenticated API endpoints for Prop Firm Risk Management and Profile Configuration."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.risk_engine import (
    BUILTIN_TEMPLATES,
    TEMPLATE_2STEP_100K,
    evaluate_account_risk,
    get_builtin_template,
)
from app.api.deps import enforce_resource_ownership, get_current_user
from app.core.errors import BadRequestError, NotFoundError
from app.db.session import get_db
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.rule import UserRule
from app.models.user import User
from app.schemas.risk import (
    AccountRiskEvaluationResponse,
    DailyLossCalculationBasis,
    DrawdownModel,
    PropRiskProfileCreate,
    PropRiskProfileResponse,
    PropRiskProfileUpdate,
    RiskEvaluationRequest,
)

router = APIRouter(prefix="/risk", tags=["Risk Management"])


def _rule_to_profile_response(rule: UserRule) -> PropRiskProfileResponse:
    """Helper to convert a UserRule ORM model into a PropRiskProfileResponse schema."""
    params = rule.parameters or {}
    return PropRiskProfileResponse(
        id=rule.id,
        user_id=rule.user_id,
        name=rule.rule_name,
        description=params.get("description"),
        initial_balance=float(params.get("initial_balance", 100000.0)),
        daily_loss_limit_pct=float(params.get("daily_loss_limit_pct", 5.0)),
        max_total_loss_limit_pct=float(params.get("max_total_loss_limit_pct", 10.0)),
        drawdown_model=DrawdownModel(params.get("drawdown_model", "STATIC")),
        daily_loss_basis=DailyLossCalculationBasis(params.get("daily_loss_basis", "EQUITY_BASED")),
        trail_locks_at_initial_balance=bool(params.get("trail_locks_at_initial_balance", True)),
        daily_reset_timezone=str(params.get("daily_reset_timezone", "UTC")),
        daily_reset_time=str(params.get("daily_reset_time", "00:00:00")),
        profit_target_pct=float(params["profit_target_pct"])
        if params.get("profit_target_pct") is not None
        else None,
        is_template=False,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


# ==============================================================================
# PROFILE CRUD ENDPOINTS
# ==============================================================================


@router.post(
    "/profiles", response_model=PropRiskProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_risk_profile(
    payload: PropRiskProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropRiskProfileResponse:
    """Create a new custom prop firm risk rule profile for the authenticated user."""
    rule_params = {
        "description": payload.description,
        "initial_balance": payload.initial_balance,
        "daily_loss_limit_pct": payload.daily_loss_limit_pct,
        "max_total_loss_limit_pct": payload.max_total_loss_limit_pct,
        "drawdown_model": payload.drawdown_model.value,
        "daily_loss_basis": payload.daily_loss_basis.value,
        "trail_locks_at_initial_balance": payload.trail_locks_at_initial_balance,
        "daily_reset_timezone": payload.daily_reset_timezone,
        "daily_reset_time": payload.daily_reset_time,
        "profit_target_pct": payload.profit_target_pct,
    }

    rule = UserRule(
        user_id=current_user.id,
        rule_name=payload.name,
        rule_type="PROP_PROFILE",
        parameters=rule_params,
        is_active=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return _rule_to_profile_response(rule)


@router.get("/profiles", response_model=list[PropRiskProfileResponse])
async def list_risk_profiles(
    include_templates: bool = Query(
        default=True, description="Include built-in example challenge templates."
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PropRiskProfileResponse]:
    """List all risk profiles available to the user (custom user profiles + example templates)."""
    stmt = (
        select(UserRule)
        .where(
            UserRule.user_id == current_user.id,
            UserRule.rule_type == "PROP_PROFILE",
        )
        .order_by(UserRule.created_at.desc())
    )
    res = await db.scalars(stmt)
    custom_profiles = [_rule_to_profile_response(r) for r in res.all()]

    if include_templates:
        return BUILTIN_TEMPLATES + custom_profiles
    return custom_profiles


@router.get("/profiles/{profile_id}", response_model=PropRiskProfileResponse)
async def get_risk_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropRiskProfileResponse:
    """Retrieve a specific risk profile by UUID or template slug identifier."""
    # Check built-in templates first
    template = get_builtin_template(profile_id)
    if template:
        return template

    # Check user-owned profiles
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError as exc:
        raise NotFoundError("PropRiskProfile", profile_id) from exc

    rule = await db.scalar(select(UserRule).where(UserRule.id == profile_uuid))
    if not rule or rule.rule_type != "PROP_PROFILE":
        raise NotFoundError("PropRiskProfile", profile_id)

    enforce_resource_ownership(rule.user_id, current_user)
    return _rule_to_profile_response(rule)


@router.put("/profiles/{profile_id}", response_model=PropRiskProfileResponse)
async def update_risk_profile(
    profile_id: str,
    payload: PropRiskProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PropRiskProfileResponse:
    """Update an existing custom risk profile owned by the authenticated user."""
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError as exc:
        raise BadRequestError(f"Built-in templates cannot be edited: '{profile_id}'") from exc

    rule = await db.scalar(select(UserRule).where(UserRule.id == profile_uuid))
    if not rule or rule.rule_type != "PROP_PROFILE":
        raise NotFoundError("PropRiskProfile", profile_id)

    enforce_resource_ownership(rule.user_id, current_user)

    params = dict(rule.parameters or {})
    if payload.name is not None:
        rule.rule_name = payload.name
    if payload.description is not None:
        params["description"] = payload.description
    if payload.initial_balance is not None:
        params["initial_balance"] = payload.initial_balance
    if payload.daily_loss_limit_pct is not None:
        params["daily_loss_limit_pct"] = payload.daily_loss_limit_pct
    if payload.max_total_loss_limit_pct is not None:
        params["max_total_loss_limit_pct"] = payload.max_total_loss_limit_pct
    if payload.drawdown_model is not None:
        params["drawdown_model"] = payload.drawdown_model.value
    if payload.daily_loss_basis is not None:
        params["daily_loss_basis"] = payload.daily_loss_basis.value
    if payload.trail_locks_at_initial_balance is not None:
        params["trail_locks_at_initial_balance"] = payload.trail_locks_at_initial_balance
    if payload.daily_reset_timezone is not None:
        params["daily_reset_timezone"] = payload.daily_reset_timezone
    if payload.daily_reset_time is not None:
        params["daily_reset_time"] = payload.daily_reset_time
    if payload.profit_target_pct is not None:
        params["profit_target_pct"] = payload.profit_target_pct

    rule.parameters = params
    await db.commit()
    await db.refresh(rule)
    return _rule_to_profile_response(rule)


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a custom risk profile owned by the authenticated user."""
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError as exc:
        raise BadRequestError(f"Built-in templates cannot be deleted: '{profile_id}'") from exc

    rule = await db.scalar(select(UserRule).where(UserRule.id == profile_uuid))
    if not rule or rule.rule_type != "PROP_PROFILE":
        raise NotFoundError("PropRiskProfile", profile_id)

    enforce_resource_ownership(rule.user_id, current_user)
    await db.delete(rule)
    await db.commit()


# ==============================================================================
# ACCOUNT RISK EVALUATION ENDPOINTS
# ==============================================================================


async def _resolve_account_and_profile(
    account_id: uuid.UUID,
    profile_id: str | None,
    current_user: User,
    db: AsyncSession,
) -> tuple[TradingAccount, PropRiskProfileResponse]:
    """Helper to fetch and validate tenant ownership of trading account and risk profile."""
    acc_stmt = select(TradingAccount).where(TradingAccount.id == account_id)
    account = await db.scalar(acc_stmt)
    if not account:
        raise NotFoundError("TradingAccount", account_id)
    enforce_resource_ownership(account.user_id, current_user)

    # Resolve profile
    if profile_id:
        template = get_builtin_template(profile_id)
        if template:
            return account, template

        try:
            p_uuid = uuid.UUID(profile_id)
        except ValueError as exc:
            raise NotFoundError("PropRiskProfile", profile_id) from exc

        rule = await db.scalar(select(UserRule).where(UserRule.id == p_uuid))
        if not rule or rule.rule_type != "PROP_PROFILE":
            raise NotFoundError("PropRiskProfile", profile_id)
        enforce_resource_ownership(rule.user_id, current_user)
        return account, _rule_to_profile_response(rule)

    # If no profile specified, use default template (or first active profile)
    return account, TEMPLATE_2STEP_100K


@router.get("/accounts/{account_id}/risk", response_model=AccountRiskEvaluationResponse)
async def get_account_risk(
    account_id: uuid.UUID,
    profile_id: str | None = Query(
        default=None,
        description="Optional profile UUID or template slug. Defaults to 2-Step 100k example.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountRiskEvaluationResponse:
    """Evaluate current risk standing of a trading account against a selected risk profile."""
    account, profile = await _resolve_account_and_profile(account_id, profile_id, current_user, db)

    # Fetch closed and open trade records
    trades_stmt = (
        select(JournalEntry)
        .where(
            JournalEntry.account_id == account.id,
            JournalEntry.user_id == current_user.id,
        )
        .order_by(JournalEntry.close_time.asc())
    )
    entries = list((await db.scalars(trades_stmt)).all())

    closed_entries = [e for e in entries if e.status == "CLOSED" and e.close_time is not None]
    open_entries = [e for e in entries if e.status in ["OPEN", "PARTIAL"]]

    return evaluate_account_risk(
        account=account,
        profile=profile,
        closed_trades=closed_entries,
        open_trades=open_entries,
        snapshot_override=None,
        profile_id=profile.id,
    )


@router.post("/accounts/{account_id}/risk/evaluate", response_model=AccountRiskEvaluationResponse)
async def evaluate_account_risk_with_snapshot(
    account_id: uuid.UUID,
    payload: RiskEvaluationRequest | None = None,
    profile_id: str | None = Query(
        default=None,
        description="Optional profile UUID or template slug. Defaults to 2-Step 100k example.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountRiskEvaluationResponse:
    """Evaluate risk with optional manual snapshot values (useful when MT5 live terminal is offline)."""
    account, profile = await _resolve_account_and_profile(account_id, profile_id, current_user, db)

    trades_stmt = (
        select(JournalEntry)
        .where(
            JournalEntry.account_id == account.id,
            JournalEntry.user_id == current_user.id,
        )
        .order_by(JournalEntry.close_time.asc())
    )
    entries = list((await db.scalars(trades_stmt)).all())

    closed_entries = [e for e in entries if e.status == "CLOSED" and e.close_time is not None]
    open_entries = [e for e in entries if e.status in ["OPEN", "PARTIAL"]]

    snapshot_override = payload.get_effective_snapshot() if payload else None

    return evaluate_account_risk(
        account=account,
        profile=profile,
        closed_trades=closed_entries,
        open_trades=open_entries,
        snapshot_override=snapshot_override,
        profile_id=profile.id,
    )
