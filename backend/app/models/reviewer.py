"""Trade review database models for TASK-013: LangGraph AI Trade Reviewer."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import TradingAccount
    from app.models.journal import JournalEntry
    from app.models.user import User


class TradeReview(Base, TenantMixin, TimestampMixin):
    """Structured AI trade review record for pre-trade setups or post-trade retrospectives."""

    __tablename__ = "trade_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trading_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # PRE_TRADE, POST_TRADE
    symbol: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    direction: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )  # BUY, SELL
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    risk_assessment: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    strategy_compliance: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    behavioral_flags: Mapped[list[dict[str, Any]]] = mapped_column(
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
    limitations: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # Relationships
    user: Mapped["User"] = relationship()
    account: Mapped["TradingAccount | None"] = relationship()
    journal_entry: Mapped["JournalEntry | None"] = relationship()
