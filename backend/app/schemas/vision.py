"""Pydantic schemas for TASK-014: AI Chart Screenshot Analyzer (Vision).

Strict typing for image upload metadata, strategy modes, market structure,
key levels, scenario analysis, playbook citations, limitations, and badges.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DataClassificationBadge
from app.schemas.reviewer import TradeDirection


class StrategyMode(str, Enum):
    """Analysis perspective framework."""

    ICT = "ICT"
    SMC = "SMC"
    PRICE_ACTION = "PRICE_ACTION"
    GENERAL = "GENERAL"


class ChartType(str, Enum):
    """Identified chart visualization type."""

    CANDLESTICK = "CANDLESTICK"
    LINE = "LINE"
    BAR = "BAR"
    HEIKIN_ASHI = "HEIKIN_ASHI"
    UNKNOWN = "UNKNOWN"


class TrendDirection(str, Enum):
    """Observable structural trend bias."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"
    UNCERTAIN = "UNCERTAIN"


class LevelType(str, Enum):
    """Classification of horizontal and zone levels."""

    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"
    ORDER_BLOCK = "ORDER_BLOCK"
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"
    LIQUIDITY_POOL = "LIQUIDITY_POOL"
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    OTHER = "OTHER"


class VisionBadge(str, Enum):
    """Taxonomy of evidence and interpretation badges for vision results."""

    AI_INTERPRETATION = "[AI INTERPRETATION]"
    OBSERVED_PATTERN = "[OBSERVED PATTERN]"
    UNVERIFIED_LEVELS = "[UNVERIFIED LEVELS]"
    PLAYBOOK_ALIGNED = "[PLAYBOOK ALIGNED]"
    PLAYBOOK_CONFLICT = "[PLAYBOOK CONFLICT]"
    INSUFFICIENT_IMAGE_EVIDENCE = "[INSUFFICIENT IMAGE EVIDENCE]"
    PROMPT_INJECTION_FLAGGED = "[PROMPT INJECTION FLAGGED]"


class KeyLevelObservation(BaseModel):
    """Observable technical or conceptual level detected on chart."""

    model_config = ConfigDict(extra="forbid")

    level_type: LevelType = Field(..., description="Type of level or structural zone")
    price_estimate: float | None = Field(
        None, description="Estimated price coordinate if axis is legible"
    )
    price_annotation: str | None = Field(
        None, description="Explicit visible price label or textual annotation"
    )
    is_annotated: bool = Field(
        False,
        description="True if explicitly marked by trader; False if inferred from price action",
    )
    description: str = Field(..., description="Observed evidence and contextual description")
    confidence: float = Field(
        0.5, ge=0.0, le=1.0, description="Visual legibility and detection confidence"
    )


class MarketStructureObservation(BaseModel):
    """Market structure analysis based on the selected framework."""

    model_config = ConfigDict(extra="forbid")

    overall_bias: TrendDirection = Field(
        TrendDirection.UNCERTAIN, description="Observed structural trend bias"
    )
    trend_description: str = Field(..., description="Description of observable trend dynamics")
    recent_swing_high: str | None = Field(
        None, description="Observed swing high location or estimated price"
    )
    recent_swing_low: str | None = Field(
        None, description="Observed swing low location or estimated price"
    )
    structure_break_observed: bool = Field(
        False, description="Whether a structural break (BOS, CHoCH, MSS) is observable"
    )
    structure_break_type: str | None = Field(
        None, description="Specific break type (e.g. BOS, CHoCH, MSS, Trendline Break)"
    )


class TradeSetupObservation(BaseModel):
    """Visible order annotations on the chart (entry, stop loss, take profit)."""

    model_config = ConfigDict(extra="forbid")

    direction: TradeDirection | None = Field(
        None, description="Inferred or annotated order direction"
    )
    entry_price: float | None = Field(None, description="Visible entry price level")
    stop_loss: float | None = Field(None, description="Visible stop loss level")
    take_profit: float | None = Field(None, description="Visible take profit level")
    is_annotated: bool = Field(
        False, description="True if marked with trading tools or explicit text"
    )
    notes: str | None = Field(None, description="Additional visible trade setup notes")


class ScenarioAnalysis(BaseModel):
    """Forward-looking scenario hypothesis with evidence and invalidation condition."""

    model_config = ConfigDict(extra="forbid")

    scenario_name: str = Field(..., description="Descriptive scenario title")
    rationale: str = Field(..., description="Observable chart rationale supporting this scenario")
    trigger_condition: str | None = Field(
        None, description="Market condition required to confirm this scenario"
    )
    invalidation_condition: str | None = Field(
        None, description="Exact observable invalidation level or event"
    )
    target_level: str | None = Field(
        None, description="Projected liquidity target or structural level"
    )
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Heuristic visual confidence")


class PlaybookCitationItem(BaseModel):
    """Personal playbook rule retrieved to compare with chart observations."""

    model_config = ConfigDict(extra="forbid")

    document_filename: str = Field(..., description="Source playbook document name")
    page: int | None = Field(None, description="Document page number if applicable")
    chunk_id: str = Field(..., description="ID of retrieved chunk")
    rule_summary: str = Field(..., description="Excerpt or summary of rule")
    citation: str = Field(..., description="Human-readable citation string")
    relevance_notes: str | None = Field(
        None, description="Notes on how this rule aligns or conflicts with chart"
    )


class ChartAnalysisResponse(BaseModel):
    """Complete structured response for an AI-assisted chart analysis."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID = Field(..., description="Unique analysis record identifier")
    user_id: uuid.UUID = Field(..., description="User ID for multi-tenant isolation")
    strategy_mode: StrategyMode = Field(..., description="Framework mode used for analysis")
    symbol: str | None = Field(None, description="Detected financial instrument symbol")
    timeframe: str | None = Field(
        None, description="Detected chart timeframe (e.g. 15m, 1h, 4h, Daily)"
    )
    chart_type: ChartType = Field(
        ChartType.UNKNOWN, description="Identified chart visualization type"
    )
    image_filename: str | None = Field(None, description="Sanitized uploaded filename")
    image_dimensions: str | None = Field(None, description="Extracted dimensions (width x height)")
    market_structure: MarketStructureObservation = Field(
        ..., description="Observable structural observations"
    )
    key_levels: list[KeyLevelObservation] = Field(
        default_factory=list, description="Extracted technical levels"
    )
    trade_setup: TradeSetupObservation | None = Field(
        None, description="Annotated trade setup if legible"
    )
    bullish_scenario: ScenarioAnalysis = Field(
        ..., description="Bullish hypothesis with invalidation"
    )
    bearish_scenario: ScenarioAnalysis = Field(
        ..., description="Bearish hypothesis with invalidation"
    )
    playbook_citations: list[PlaybookCitationItem] = Field(
        default_factory=list, description="Relevant personal playbook rules"
    )
    limitations: list[str] = Field(
        default_factory=list, description="Explicit image limitations and missing context"
    )
    badges: list[VisionBadge] = Field(
        default_factory=list, description="Visual classification badges"
    )
    uncertainty_rating: float = Field(
        0.0, ge=0.0, le=1.0, description="Overall analysis uncertainty (0=clear, 1=uncertain)"
    )
    executive_summary: str = Field(
        ..., description="Synthesized executive review of chart findings"
    )
    data_classification_badge: DataClassificationBadge = Field(
        DataClassificationBadge.AI_INTERPRETATION,
        description="Mandatory system classification badge",
    )
    created_at: datetime = Field(..., description="Timestamp when analysis was generated")
