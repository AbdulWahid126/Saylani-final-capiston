import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import TradingAccount
    from app.models.journal import DealJournalMapping


class RawMT5Deal(Base, TimestampMixin):
    """Immutable audit record of a raw broker deal execution from MT5."""

    __tablename__ = "raw_mt5_deals"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deal_ticket: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    order_ticket: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    position_ticket: Mapped[int] = mapped_column(
        BigInteger,
        index=True,
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(
        String(30),
        index=True,
        nullable=False,
    )
    deal_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # BUY, SELL
    entry_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # IN, OUT, INOUT
    volume: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    profit: Mapped[float] = mapped_column(
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
    fee: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    deal_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )

    # Relationships
    account: Mapped["TradingAccount"] = relationship(
        back_populates="raw_deals",
    )
    journal_mappings: Mapped[list["DealJournalMapping"]] = relationship(
        back_populates="raw_deal",
        cascade="all, delete-orphan",
    )
