"""Pydantic v2 schemas for Trading Behavior Analyzer.

Defines schemas for deterministic behavioral pattern findings, evidence,
configuration models, pattern summaries, and overall behavioral health metrics.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import DataClassificationBadge


class BehaviorPatternType(str, Enum):
    """Categorized behavioral pattern types."""

    RAPID_REENTRY_AFTER_LOSS = "rapid_reentry_after_loss"
    OVERTRADING_FREQUENCY = "overtrading_frequency"
    RISK_ESCALATION = "risk_escalation"
    SESSION_DRIFT = "session_drift"


class BehaviorSeverity(str, Enum):
    """Severity classification for behavioral findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ThresholdSource(str, Enum):
    """Identifies whether an analysis threshold was user-specified or baseline-inferred."""

    USER_CONFIGURED = "user_configured"
    BASELINE_INFERRED = "baseline_inferred"
    DEFAULT_STANDARD = "default_standard"


class BehaviorFinding(BaseModel):
    """An objective, factual finding detailing an observed behavioral trading pattern."""

    id: str = Field(description="Unique finding identifier.")
    pattern_type: BehaviorPatternType = Field(description="Behavior pattern type.")
    severity: BehaviorSeverity = Field(description="Evaluated severity level (LOW, MEDIUM, HIGH).")
    title: str = Field(description="Concise factual description of the observed finding.")
    description: str = Field(
        description="Detailed objective description without psychiatric or clinical diagnostic language."
    )
    detected_at: datetime = Field(description="Timestamp when the pattern was manifested.")
    trade_id: str | None = Field(
        default=None,
        description="Primary journal entry ID associated with the finding.",
    )
    related_trade_ids: list[str] = Field(
        default_factory=list,
        description="Associated prior or concurrent trade IDs (e.g. prior loss trade).",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured numerical/factual evidence supporting the observation.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score in the finding based on data completeness.",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Known limitations or caveats for this specific observation.",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Objective, non-clinical trading review actions recommended to the trader.",
    )


class BehaviorAnalysisConfig(BaseModel):
    """Configurable parameters for deterministic behavior pattern analysis."""

    reentry_window_minutes: int = Field(
        default=15,
        ge=1,
        le=1440,
        description="Window in minutes to evaluate rapid trade re-entry following a closed loss.",
    )
    max_trades_per_day: int | None = Field(
        default=None,
        ge=1,
        le=1000,
        description="Explicit user threshold for max trades per calendar day. If None, historical baseline is inferred.",
    )
    max_trades_per_session: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description="Explicit user threshold for max trades per session tag. If None, historical baseline is inferred.",
    )
    size_escalation_ratio: float = Field(
        default=1.5,
        ge=1.01,
        le=20.0,
        description="Multiplier threshold identifying position size escalation after a loss (e.g., 1.5 = 50% larger).",
    )
    size_lookback_trades: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of preceding loss trades to compare sizing against.",
    )
    compare_same_symbol_only: bool = Field(
        default=True,
        description="When true, size escalation compares trades within the same instrument to prevent contract size distortion.",
    )
    allowed_sessions: list[str] | None = Field(
        default=None,
        description="User's configured active sessions (e.g., ['LONDON', 'NY_AM']).",
    )
    session_start_time: str | None = Field(
        default=None,
        description="Allowed daily trading window start time in 'HH:MM:SS' format.",
    )
    session_end_time: str | None = Field(
        default=None,
        description="Allowed daily trading window end time in 'HH:MM:SS' format.",
    )
    session_timezone: str | None = Field(
        default=None,
        description="IANA timezone for session boundaries (e.g., 'America/New_York', 'UTC').",
    )


class BehaviorPatternSummary(BaseModel):
    """Aggregate summary metrics for a specific behavioral pattern type."""

    pattern_type: BehaviorPatternType = Field(description="Behavior pattern type.")
    pattern_name: str = Field(description="Human-readable pattern label.")
    occurrences_count: int = Field(description="Total occurrences detected in analyzed dataset.")
    severity_breakdown: dict[str, int] = Field(
        description="Count of findings per severity level (e.g. {'LOW': 0, 'MEDIUM': 2, 'HIGH': 1})."
    )
    first_detected_at: datetime | None = Field(
        default=None,
        description="Earliest finding timestamp.",
    )
    last_detected_at: datetime | None = Field(
        default=None,
        description="Most recent finding timestamp.",
    )
    summary_notes: str = Field(description="High-level statistical observation.")


class BehaviorSummaryResponse(BaseModel):
    """Comprehensive behavioral analysis response for an account or user."""

    account_id: uuid.UUID | None = Field(
        default=None,
        description="Scoped trading account ID, or None if aggregated across user accounts.",
    )
    total_trades_analyzed: int = Field(description="Total position journal entries evaluated.")
    total_findings: int = Field(description="Total objective behavioral flags detected.")
    high_severity_count: int = Field(description="Number of HIGH severity findings.")
    medium_severity_count: int = Field(description="Number of MEDIUM severity findings.")
    low_severity_count: int = Field(description="Number of LOW severity findings.")
    overall_discipline_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Deterministic behavioral discipline score (0-100) based on finding frequency and severity.",
    )
    pattern_summaries: list[BehaviorPatternSummary] = Field(
        description="Summary breakdowns per pattern type."
    )
    findings: list[BehaviorFinding] = Field(
        description="Chronological or prioritized list of detailed findings."
    )
    data_limitations: list[str] = Field(
        default_factory=list,
        description="General data limitations (e.g. missing timestamps, insufficient baseline history, unconfigured sessions).",
    )
    configuration_used: BehaviorAnalysisConfig = Field(
        description="Effective configuration parameters used for the analysis."
    )
    data_badge: DataClassificationBadge = Field(
        default=DataClassificationBadge.HISTORICAL_STATISTICS,
        description="Mandatory visual data distinction badge.",
    )


class BehaviorFindingsResponse(BaseModel):
    """Detailed list response for behavioral findings with filtering and pagination info."""

    total_findings: int = Field(description="Total findings matching filter criteria.")
    findings: list[BehaviorFinding] = Field(description="List of detected behavioral findings.")
    data_badge: DataClassificationBadge = Field(
        default=DataClassificationBadge.HISTORICAL_STATISTICS,
        description="Mandatory visual data distinction badge.",
    )


class BehaviorUserConfigRequest(BaseModel):
    """Request payload to save or update user behavioral configuration rules."""

    config: BehaviorAnalysisConfig = Field(
        description="Behavioral analysis configuration parameters."
    )


class BehaviorUserConfigResponse(BaseModel):
    """Response payload containing saved user behavioral configuration."""

    id: str = Field(description="Config rule ID.")
    user_id: str = Field(description="Owner user ID.")
    rule_name: str = Field(description="Rule name.")
    config: BehaviorAnalysisConfig = Field(description="Configured behavioral analysis parameters.")
    is_active: bool = Field(description="Active status of this behavioral configuration.")
    updated_at: datetime | None = Field(
        default=None,
        description="Last updated timestamp.",
    )


class BehaviorAnalyzeRequest(BaseModel):
    """On-demand behavioral analysis request with custom parameters."""

    account_id: uuid.UUID | None = Field(
        default=None,
        description="Optional account ID filter.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Optional start date filter (inclusive).",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Optional end date filter (inclusive).",
    )
    symbol: str | None = Field(
        default=None,
        description="Optional instrument symbol filter.",
    )
    config: BehaviorAnalysisConfig = Field(
        default_factory=BehaviorAnalysisConfig,
        description="Custom behavioral parameters to evaluate.",
    )
