"""Pydantic schemas for TASK-013: LangGraph AI Trade Reviewer (Pre & Post-Trade).

Strict typing for pre-trade input validation, post-trade context,
risk assessments, playbook evidence items, behavioral context, and badges.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.behavior import BehaviorPatternType, BehaviorSeverity
from app.schemas.common import DataClassificationBadge
from app.schemas.risk import RiskStatusLevel


class ReviewMode(str, Enum):
    """Execution mode of the AI Trade Reviewer."""

    PRE_TRADE = "PRE_TRADE"
    POST_TRADE = "POST_TRADE"


class TradeDirection(str, Enum):
    """Trading order direction."""

    BUY = "BUY"
    SELL = "SELL"


class ReviewBadge(str, Enum):
    """Deterministic badge taxonomy with strict precedence rules."""

    RISK_WITHIN_CONFIGURED_LIMITS = "RISK_WITHIN_CONFIGURED_LIMITS"
    RISK_WARNING = "RISK_WARNING"
    RISK_LIMIT_BREACHED = "RISK_LIMIT_BREACHED"
    PLAYBOOK_MATCH = "PLAYBOOK_MATCH"
    PLAYBOOK_CONFLICT = "PLAYBOOK_CONFLICT"
    BEHAVIORAL_PATTERN_DETECTED = "BEHAVIORAL_PATTERN_DETECTED"
    MISSING_STOP_LOSS = "MISSING_STOP_LOSS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REVIEW_INCOMPLETE = "REVIEW_INCOMPLETE"


class PreTradeReviewRequest(BaseModel):
    """Input payload for a pre-trade setup analysis."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Financial instrument symbol, e.g. EURUSD, XAUUSD",
    )
    side: TradeDirection = Field(..., description="Trade direction (BUY or SELL)")
    entry_price: float = Field(..., gt=0.0, description="Proposed order entry price")
    stop_loss: float | None = Field(None, gt=0.0, description="Proposed protective stop loss price")
    take_profit: float | None = Field(None, gt=0.0, description="Proposed profit target price")
    volume: float = Field(..., gt=0.0, description="Order volume in lots")
    account_id: uuid.UUID | None = Field(
        None, description="Target trading account ID for risk context"
    )
    strategy_name: str | None = Field(
        None, max_length=100, description="Strategy name for playbook rule matching"
    )
    user_checklist_notes: str | None = Field(
        None, max_length=3000, description="Trader's setup checklist notes or justification"
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.upper().strip()


class PostTradeReviewRequest(BaseModel):
    """Input payload for a post-trade retrospective analysis."""

    model_config = ConfigDict(extra="forbid")

    journal_entry_id: uuid.UUID | None = Field(
        None, description="UUID of the closed trade in journal"
    )
    deal_ticket: str | None = Field(
        None, max_length=50, description="Broker deal ticket if journal_entry_id not provided"
    )
    account_id: uuid.UUID | None = Field(None, description="Account ID for deal ticket lookup")
    strategy_name: str | None = Field(
        None, max_length=100, description="Optional override strategy name"
    )
    notes: str | None = Field(
        None, max_length=3000, description="Trader's post-trade retrospective comments"
    )


class RiskAssessmentResult(BaseModel):
    """Deterministic risk analysis metrics and prop firm rule checks."""

    account_balance: float | None = None
    account_equity: float | None = None
    daily_drawdown_pct: float | None = None
    max_drawdown_pct: float | None = None
    daily_loss_allowance_remaining: float | None = None
    risk_status: RiskStatusLevel = RiskStatusLevel.UNAVAILABLE
    risk_reward_ratio: float | None = None
    monetary_risk_amount: float | None = None
    risk_percent_of_balance: float | None = None
    is_stop_loss_missing: bool = False
    risk_explanation: str


class PlaybookEvidenceItem(BaseModel):
    """Retrieved user playbook rule supporting or warning against the trade."""

    document_filename: str
    page: int | None = None
    chunk_id: str
    rule_summary: str
    match_strength: str  # STRONG, MODERATE, WEAK
    citation: str
    compliance_status: str  # ALIGNED, CONFLICTING, INSUFFICIENT_CONTEXT


class BehaviorContextItem(BaseModel):
    """Detected historical behavioral patterns relevant to current trading context."""

    pattern_type: BehaviorPatternType
    severity: BehaviorSeverity
    title: str
    description: str
    evidence: str


class TradeReviewResponse(BaseModel):
    """Complete, structured, and explainable AI Trade Reviewer response."""

    id: uuid.UUID
    mode: ReviewMode
    user_id: uuid.UUID
    account_id: uuid.UUID | None = None
    journal_entry_id: uuid.UUID | None = None
    symbol: str
    direction: str | None = None
    summary: str
    risk_assessment: RiskAssessmentResult
    strategy_compliance: list[PlaybookEvidenceItem] = Field(default_factory=list)
    behavioral_flags: list[BehaviorContextItem] = Field(default_factory=list)
    badges: list[ReviewBadge] = Field(default_factory=list)
    uncertainty_rating: float = Field(0.0, ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)
    data_classification_badge: DataClassificationBadge = DataClassificationBadge.AI_INTERPRETATION
    created_at: datetime
