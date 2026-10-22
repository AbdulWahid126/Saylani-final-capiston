"""Pydantic v2 schemas for the Prop Firm Risk Manager Engine."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DrawdownModel(str, Enum):
    """Drawdown limit calculation model."""

    STATIC = "STATIC"
    TRAILING = "TRAILING"


class DailyLossCalculationBasis(str, Enum):
    """Reference basis for daily loss calculation."""

    BALANCE_BASED = "BALANCE_BASED"
    EQUITY_BASED = "EQUITY_BASED"


class RiskStatusLevel(str, Enum):
    """Visual classification of risk limit utilization."""

    GREEN = "GREEN"  # < 50% utilization (Safe)
    AMBER = "AMBER"  # 50% - 80% utilization (Caution)
    RED = "RED"  # > 80% utilization (Warning / High Risk)
    BREACHED = "BREACHED"  # >= 100% utilization (Violation)
    UNAVAILABLE = "UNAVAILABLE"  # Critical input data missing or stale


class PropRiskProfileBase(BaseModel):
    """Base configuration parameters for a prop firm risk rule profile."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        min_length=1, max_length=100, description="Display name for this risk profile."
    )
    description: str | None = Field(
        default=None, max_length=255, description="Brief description or prop firm reference."
    )
    initial_balance: float = Field(
        gt=0.0, description="Reference / starting account balance (e.g. 100000.0)."
    )
    daily_loss_limit_pct: float = Field(
        gt=0.0,
        le=50.0,
        description="Daily loss limit as percentage of reference balance (e.g. 5.0 for 5%).",
    )
    max_total_loss_limit_pct: float = Field(
        gt=0.0,
        le=50.0,
        description="Maximum total loss limit as percentage of reference balance (e.g. 10.0 for 10%).",
    )
    drawdown_model: DrawdownModel = Field(
        default=DrawdownModel.STATIC,
        description="STATIC (relative to initial balance) or TRAILING (relative to high-water mark).",
    )
    daily_loss_basis: DailyLossCalculationBasis = Field(
        default=DailyLossCalculationBasis.EQUITY_BASED,
        description="BALANCE_BASED (closed trades only) or EQUITY_BASED (includes floating P&L).",
    )
    trail_locks_at_initial_balance: bool = Field(
        default=True,
        description="If True in TRAILING mode, trailing floor stops rising once it reaches initial balance.",
    )
    daily_reset_timezone: str = Field(
        default="UTC",
        description="IANA Timezone name for daily reset (e.g., 'UTC', 'America/New_York', 'Europe/Prague').",
    )
    daily_reset_time: str = Field(
        default="00:00:00",
        description="Daily reset time in HH:MM:SS format within configured timezone.",
    )
    profit_target_pct: float | None = Field(
        default=None,
        gt=0.0,
        le=100.0,
        description="Optional profit target percentage for evaluation challenge (e.g. 10.0 for 10%).",
    )
    is_template: bool = Field(
        default=False, description="Flag indicating if this is a built-in example template."
    )


class PropRiskProfileCreate(PropRiskProfileBase):
    """Request payload to create a custom user risk profile."""

    pass


class PropRiskProfileUpdate(BaseModel):
    """Request payload to update an existing user risk profile."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    initial_balance: float | None = Field(default=None, gt=0.0)
    daily_loss_limit_pct: float | None = Field(default=None, gt=0.0, le=50.0)
    max_total_loss_limit_pct: float | None = Field(default=None, gt=0.0, le=50.0)
    drawdown_model: DrawdownModel | None = None
    daily_loss_basis: DailyLossCalculationBasis | None = None
    trail_locks_at_initial_balance: bool | None = None
    daily_reset_timezone: str | None = None
    daily_reset_time: str | None = None
    profit_target_pct: float | None = Field(default=None, gt=0.0, le=100.0)


class PropRiskProfileResponse(PropRiskProfileBase):
    """Response schema for a persisted or template risk profile."""

    id: uuid.UUID | str = Field(description="Profile UUID or template slug identifier.")
    user_id: uuid.UUID | None = Field(
        default=None, description="User UUID, or None for public templates."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DailyRiskStatus(BaseModel):
    """Detailed daily drawdown limit status."""

    start_of_day_balance: float = Field(
        description="Balance at the start of the current trading day."
    )
    daily_closed_pnl: float = Field(
        description="Net realized P&L of trades closed after today's reset time."
    )
    current_floating_pnl: float = Field(description="Floating P&L of currently open positions.")
    effective_daily_loss: float = Field(
        ge=0.0, description="Current loss incurred today based on profile basis ($)."
    )
    daily_loss_limit_amount: float = Field(
        gt=0.0, description="Configured maximum daily loss allowance ($)."
    )
    daily_loss_remaining: float = Field(
        ge=0.0, description="Remaining daily loss allowance before breach ($)."
    )
    daily_loss_utilization_pct: float = Field(
        ge=0.0, description="Percentage of daily loss limit consumed (%)."
    )
    status_level: RiskStatusLevel = Field(
        description="GREEN (<50%), AMBER (50-80%), RED (>80%), BREACHED (>=100%)."
    )
    reset_timestamp_utc: datetime = Field(
        description="UTC timestamp when the current daily session began."
    )
    next_reset_timestamp_utc: datetime = Field(
        description="UTC timestamp when the next daily reset will occur."
    )
    is_breached: bool = Field(default=False)
    explanation: str = Field(
        description="Human-readable explanation of current daily risk standing."
    )


class OverallRiskStatus(BaseModel):
    """Detailed maximum total / trailing drawdown limit status."""

    initial_reference_balance: float = Field(description="Initial challenge balance baseline.")
    peak_high_water_mark: float = Field(description="Highest peak balance/equity observed.")
    current_equity: float = Field(description="Current account equity.")
    hard_floor_level: float = Field(description="Minimum equity level allowed before breach ($).")
    overall_loss_limit_amount: float = Field(
        gt=0.0, description="Maximum total loss allowance ($)."
    )
    overall_loss_current: float = Field(
        ge=0.0, description="Current loss from initial or high-water mark ($)."
    )
    overall_loss_remaining: float = Field(
        ge=0.0, description="Remaining overall loss buffer before breach ($)."
    )
    overall_loss_utilization_pct: float = Field(
        ge=0.0, description="Percentage of overall loss limit consumed (%)."
    )
    drawdown_model_used: DrawdownModel = Field(description="STATIC or TRAILING.")
    status_level: RiskStatusLevel = Field(
        description="GREEN (<50%), AMBER (50-80%), RED (>80%), BREACHED (>=100%)."
    )
    is_breached: bool = Field(default=False)
    explanation: str = Field(
        description="Human-readable explanation of current overall risk standing."
    )


class ProfitTargetStatus(BaseModel):
    """Optional prop firm profit target progress status."""

    target_amount: float = Field(ge=0.0, description="Monetary profit target required to pass.")
    current_profit: float = Field(description="Current profit above initial reference balance.")
    remaining_profit_required: float = Field(ge=0.0, description="Profit needed to achieve target.")
    progress_percentage: float = Field(
        ge=0.0, le=100.0, description="Percentage towards target completion (0-100%)."
    )
    target_achieved: bool = Field(default=False)


class RiskSnapshotOverride(BaseModel):
    """Optional manual snapshot input for evaluating risk when live MT5 data is offline."""

    current_balance: float | None = Field(
        default=None, gt=0.0, description="Override account current balance."
    )
    current_equity: float | None = Field(
        default=None, gt=0.0, description="Override account current equity."
    )
    current_floating_pnl: float | None = Field(
        default=None, description="Override floating P&L of open positions."
    )


class RiskEvaluationRequest(BaseModel):
    """Request payload for risk evaluation supporting direct or nested snapshot override."""

    snapshot_override: RiskSnapshotOverride | None = None
    current_balance: float | None = Field(default=None, gt=0.0)
    current_equity: float | None = Field(default=None, gt=0.0)
    current_floating_pnl: float | None = None

    def get_effective_snapshot(self) -> RiskSnapshotOverride | None:
        if self.snapshot_override is not None:
            return self.snapshot_override
        if (
            self.current_balance is not None
            or self.current_equity is not None
            or self.current_floating_pnl is not None
        ):
            return RiskSnapshotOverride(
                current_balance=self.current_balance,
                current_equity=self.current_equity,
                current_floating_pnl=self.current_floating_pnl,
            )
        return None


class AccountRiskEvaluationResponse(BaseModel):
    """Comprehensive risk evaluation report for a trading account."""

    account_id: uuid.UUID
    account_number: str
    broker_name: str
    currency: str
    profile_id: uuid.UUID | str
    profile_name: str
    is_live_sync_active: bool = Field(
        description="Whether MT5 live connection was active or manual snapshot was used."
    )
    evaluated_at: datetime
    is_data_available: bool = Field(
        default=True, description="False if critical account data is missing/invalid."
    )
    data_availability_notes: str | None = None

    overall_status_level: RiskStatusLevel = Field(
        description="Worst-case status: GREEN, AMBER, RED, BREACHED, UNAVAILABLE."
    )
    is_any_limit_breached: bool = Field(
        default=False, description="True if either daily or total limit is breached."
    )
    summary_warning_message: str = Field(
        description="Summary actionable advisory for trader or risk gauges."
    )

    daily_risk: DailyRiskStatus
    overall_risk: OverallRiskStatus
    profit_target: ProfitTargetStatus | None = None
