import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import TradingAccount
    from app.models.journal import JournalEntry
    from app.models.knowledge import DocumentKnowledge
    from app.models.reviewer import TradeReview
    from app.models.rule import UserRule
    from app.models.strategy import Strategy
    from app.models.vision import ChartAnalysis


class User(Base, TimestampMixin):
    """User account model adhering to multi-tenant isolation."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    base_currency: Mapped[str] = mapped_column(
        String(10),
        default="USD",
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
    )

    # Relationships
    trading_accounts: Mapped[list["TradingAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    strategies: Mapped[list["Strategy"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    user_rules: Mapped[list["UserRule"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    journal_entries: Mapped[list["JournalEntry"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    document_knowledge: Mapped[list["DocumentKnowledge"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    trade_reviews: Mapped[list["TradeReview"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chart_analyses: Mapped[list["ChartAnalysis"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
