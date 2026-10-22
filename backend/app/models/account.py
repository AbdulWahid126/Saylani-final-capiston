import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.deal import RawMT5Deal
    from app.models.journal import JournalEntry
    from app.models.user import User


class TradingAccount(Base, TenantMixin, TimestampMixin):
    """Trading account entity supporting MT5 live/demo and prop firm tracking."""

    __tablename__ = "trading_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    broker_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    server_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    account_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    account_type: Mapped[str] = mapped_column(
        String(30),
        default="DEMO",
        nullable=False,
    )  # LIVE, DEMO, PROP_CHALLENGE, PROP_FUNDED
    encrypted_investor_pwd: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    balance: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    equity: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    initial_balance: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        nullable=False,
    )
    leverage: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )
    sync_status: Mapped[str] = mapped_column(
        String(20),
        default="DISCONNECTED",
        nullable=False,
    )  # IDLE, SYNCING, ERROR, DISCONNECTED
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="trading_accounts",
    )
    raw_deals: Mapped[list["RawMT5Deal"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )
    journal_entries: Mapped[list["JournalEntry"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )
