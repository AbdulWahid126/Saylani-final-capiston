"""Chart analysis database models for TASK-014: AI Chart Screenshot Analyzer."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ChartAnalysis(Base, TenantMixin, TimestampMixin):
    """Structured AI chart screenshot analysis record."""

    __tablename__ = "chart_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="GENERAL",
        index=True,
    )  # ICT, SMC, PRICE_ACTION, GENERAL
    symbol: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
    )
    timeframe: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    chart_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )  # CANDLESTICK, LINE, BAR, HEIKIN_ASHI
    image_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    image_dimensions: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g. "1920x1080"
    market_structure: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    key_levels: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    trade_setup: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    scenarios: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )  # Contains bullish_scenario and bearish_scenario
    playbook_citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    limitations: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    badges: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    uncertainty_rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    executive_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="chart_analyses",
    )
