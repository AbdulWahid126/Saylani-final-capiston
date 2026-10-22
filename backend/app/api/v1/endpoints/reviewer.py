"""FastAPI endpoints for TASK-013: LangGraph AI Trade Reviewer (Pre & Post-Trade).

Provides authenticated endpoints for:
- Pre-trade setup analysis with deterministic risk checks, playbook rules, and behavioral flags.
- Post-trade retrospective analysis with journal data comparison.
- Historical review retrieval, listing, and deletion under strict multi-tenant isolation.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.errors import NotFoundError
from app.models.reviewer import TradeReview
from app.models.user import User
from app.schemas.common import DataClassificationBadge
from app.schemas.reviewer import (
    BehaviorContextItem,
    PlaybookEvidenceItem,
    PostTradeReviewRequest,
    PreTradeReviewRequest,
    ReviewBadge,
    ReviewMode,
    RiskAssessmentResult,
    TradeReviewResponse,
)
from app.services.trade_reviewer import run_post_trade_review, run_pre_trade_review

router = APIRouter(prefix="/reviewer", tags=["AI Trade Reviewer"])


@router.post(
    "/pre-trade",
    response_model=TradeReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Pre-Trade AI review using LangGraph state machine",
)
async def review_pre_trade(
    payload: PreTradeReviewRequest,
    persist: bool = Query(True, description="Persist review in database history"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradeReviewResponse:
    """Evaluates planned order setup against risk limits, personal playbook rules, and recent behavioral patterns."""
    return await run_pre_trade_review(
        db=db,
        user_id=current_user.id,
        payload=payload,
        persist=persist,
    )


@router.post(
    "/post-trade",
    response_model=TradeReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Post-Trade retrospective review using LangGraph state machine",
)
async def review_post_trade(
    payload: PostTradeReviewRequest,
    persist: bool = Query(True, description="Persist review in database history"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradeReviewResponse:
    """Audits closed trade journal entry against personal playbook rules and deterministic financial metrics."""
    return await run_post_trade_review(
        db=db,
        user_id=current_user.id,
        payload=payload,
        persist=persist,
    )


@router.get(
    "/reviews",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="List saved AI trade reviews with pagination",
)
async def list_reviews(
    mode: ReviewMode | None = Query(
        None, description="Filter by review mode (PRE_TRADE or POST_TRADE)"
    ),
    journal_entry_id: uuid.UUID | None = Query(
        None, description="Filter by associated journal entry ID"
    ),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves paginated trade review history for the authenticated user."""
    stmt = select(TradeReview).where(TradeReview.user_id == current_user.id)
    count_stmt = select(func.count(TradeReview.id)).where(TradeReview.user_id == current_user.id)

    if mode:
        stmt = stmt.where(TradeReview.mode == mode.value)
        count_stmt = count_stmt.where(TradeReview.mode == mode.value)

    if journal_entry_id:
        stmt = stmt.where(TradeReview.journal_entry_id == journal_entry_id)
        count_stmt = count_stmt.where(TradeReview.journal_entry_id == journal_entry_id)

    total = await db.scalar(count_stmt) or 0
    records = list(
        (
            await db.scalars(
                stmt.order_by(TradeReview.created_at.desc()).offset(offset).limit(limit)
            )
        ).all()
    )

    items: list[dict[str, Any]] = []
    for r in records:
        badges_enums = [
            ReviewBadge(b) for b in (r.badges or []) if b in ReviewBadge._value2member_map_
        ]
        items.append(
            {
                "id": r.id,
                "mode": r.mode,
                "user_id": r.user_id,
                "account_id": r.account_id,
                "journal_entry_id": r.journal_entry_id,
                "symbol": r.symbol,
                "direction": r.direction,
                "summary": r.summary,
                "risk_assessment": r.risk_assessment,
                "strategy_compliance": r.strategy_compliance,
                "behavioral_flags": r.behavioral_flags,
                "badges": badges_enums,
                "uncertainty_rating": r.uncertainty_rating,
                "limitations": r.limitations,
                "data_classification_badge": DataClassificationBadge.AI_INTERPRETATION,
                "created_at": r.created_at,
            }
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/reviews/{id}",
    response_model=TradeReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single trade review by ID",
)
async def get_review(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradeReviewResponse:
    """Retrieves details of a previously persisted trade review."""
    stmt = select(TradeReview).where(
        TradeReview.id == id,
        TradeReview.user_id == current_user.id,
    )
    r = (await db.scalars(stmt)).first()
    if not r:
        raise NotFoundError("Trade review not found or access denied")

    risk_dict = r.risk_assessment or {}
    badges_enums = [ReviewBadge(b) for b in (r.badges or []) if b in ReviewBadge._value2member_map_]

    return TradeReviewResponse(
        id=r.id,
        mode=ReviewMode(r.mode),
        user_id=r.user_id,
        account_id=r.account_id,
        journal_entry_id=r.journal_entry_id,
        symbol=r.symbol,
        direction=r.direction,
        summary=r.summary,
        risk_assessment=RiskAssessmentResult(**risk_dict),
        strategy_compliance=[
            PlaybookEvidenceItem(**item) for item in (r.strategy_compliance or [])
        ],
        behavioral_flags=[BehaviorContextItem(**item) for item in (r.behavioral_flags or [])],
        badges=badges_enums,
        uncertainty_rating=r.uncertainty_rating,
        limitations=r.limitations or [],
        data_classification_badge=DataClassificationBadge.AI_INTERPRETATION,
        created_at=r.created_at,
    )


@router.delete(
    "/reviews/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a persisted trade review",
)
async def delete_review(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a previously persisted trade review owned by the authenticated user."""
    stmt = select(TradeReview).where(
        TradeReview.id == id,
        TradeReview.user_id == current_user.id,
    )
    r = (await db.scalars(stmt)).first()
    if not r:
        raise NotFoundError("Trade review not found or access denied")

    await db.delete(r)
    await db.commit()
