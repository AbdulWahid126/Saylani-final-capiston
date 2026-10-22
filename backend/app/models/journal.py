import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import TradingAccount
    from app.models.deal import RawMT5Deal
    from app.models.strategy import Strategy
    from app.models.user import User


class JournalEntry(Base, TenantMixin, TimestampMixin):
    """Unified trade journal entry representing an aggregated position lifecycle."""

    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    broker_position_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String(30),
        index=True,
        nullable=False,
    )
    direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )  # BUY, SELL
    volume: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    entry_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    exit_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    stop_loss: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    take_profit: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    gross_profit: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    commission: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    swap: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    net_pnl: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    risk_amount: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    risk_percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    rr_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    open_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    close_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="OPEN",
        nullable=False,
    )  # OPEN, CLOSED, PARTIAL
    session: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # ASIA, LONDON, NY_AM, NY_PM
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
    )
    setup_tag: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    user_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    emotional_state: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    idempotency_hash: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=True,
    )

    # Relationships
    account: Mapped["TradingAccount"] = relationship(
        back_populates="journal_entries",
    )
    user: Mapped["User"] = relationship(
        back_populates="journal_entries",
    )
    strategy: Mapped["Strategy | None"] = relationship(
        back_populates="journal_entries",
    )
    deal_mappings: Mapped[list["DealJournalMapping"]] = relationship(
        back_populates="journal_entry",
        cascade="all, delete-orphan",
    )


class DealJournalMapping(Base, TimestampMixin):
    """Associative mapping table linking individual raw deals to aggregated journal entries."""

    __tablename__ = "deal_journal_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_mt5_deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    journal_entry: Mapped["JournalEntry"] = relationship(
        back_populates="deal_mappings",
    )
    raw_deal: Mapped["RawMT5Deal"] = relationship(
        back_populates="journal_mappings",
    )
