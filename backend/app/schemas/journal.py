"""Schemas for Trading Journal, Manual Entry, and CSV Trade Import."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class JournalEntryBase(BaseModel):
    """Core trade journal schema representing a complete position."""

    account_id: uuid.UUID = Field(..., description="Target trading account UUID")
    symbol: str = Field(..., min_length=1, max_length=30, description="Financial asset symbol")
    direction: Literal["BUY", "SELL"] = Field(..., description="Trade direction: BUY or SELL")
    volume: float = Field(..., gt=0.0, description="Position size in lots")
    entry_price: float = Field(..., gt=0.0, description="Execution open price")
    exit_price: float | None = Field(None, gt=0.0, description="Execution close price")
    stop_loss: float | None = Field(None, gt=0.0, description="Stop loss price")
    take_profit: float | None = Field(None, gt=0.0, description="Take profit price")
    gross_profit: float = Field(0.0, description="Gross realized profit in account currency")
    commission: float = Field(0.0, description="Broker execution commission")
    swap: float = Field(0.0, description="Overnight financing charges")
    net_pnl: float | None = Field(
        None, description="Net realized profit including commission and swap"
    )
    risk_amount: float | None = Field(
        None, ge=0.0, description="Calculated dollar risk at stop loss"
    )
    risk_percentage: float | None = Field(None, ge=0.0, description="Calculated percentage risk")
    rr_ratio: float | None = Field(None, ge=0.0, description="Calculated risk-to-reward ratio")
    open_time: datetime = Field(..., description="Position open timestamp (UTC)")
    close_time: datetime | None = Field(None, description="Position close timestamp (UTC)")
    status: Literal["OPEN", "CLOSED", "PARTIAL"] = Field(
        "OPEN", description="Trade lifecycle state"
    )
    session: Literal["ASIA", "LONDON", "NY_AM", "NY_PM"] | None = Field(
        None, description="Trading session when position was opened"
    )
    strategy_id: uuid.UUID | None = Field(
        None, description="Associated trading playbook strategy UUID"
    )
    setup_tag: str | None = Field(
        None, max_length=50, description="Pattern or setup classification tag"
    )
    user_notes: str | None = Field(None, description="Discretionary post-trade notes or review")
    emotional_state: str | None = Field(
        None, max_length=50, description="Psychological mindset tag"
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: Any) -> str:
        if isinstance(v, str):
            clean = v.strip().upper()
            if not clean:
                raise ValueError("Symbol cannot be empty.")
            return clean
        return str(v)

    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, v: Any) -> str:
        if isinstance(v, str):
            clean = v.strip().upper()
            if clean in ("BUY", "LONG", "0"):
                return "BUY"
            elif clean in ("SELL", "SHORT", "1"):
                return "SELL"
        raise ValueError("Direction must be 'BUY' or 'SELL'.")


class JournalEntryCreate(JournalEntryBase):
    """Payload for creating a manual journal entry."""

    @model_validator(mode="after")
    def validate_manual_entry(self) -> "JournalEntryCreate":
        # 1. Deterministic status and close time checks
        if self.close_time and self.open_time:
            if self.close_time < self.open_time:
                raise ValueError("close_time cannot be earlier than open_time.")
            if self.exit_price is not None and self.status == "OPEN":
                self.status = "CLOSED"

        if self.status == "CLOSED":
            if self.exit_price is None:
                raise ValueError("exit_price is required for CLOSED trades.")
            if self.close_time is None:
                raise ValueError("close_time is required for CLOSED trades.")

        # 2. Deterministic Net P&L calculation if omitted
        if self.net_pnl is None:
            self.net_pnl = round(self.gross_profit + self.commission + self.swap, 4)
        else:
            self.net_pnl = round(self.net_pnl, 4)

        # 3. Deterministic R:R calculation if stop loss and take profit are provided
        if self.stop_loss is not None and self.take_profit is not None and self.rr_ratio is None:
            if self.direction == "BUY":
                risk = self.entry_price - self.stop_loss
                reward = self.take_profit - self.entry_price
            else:
                risk = self.stop_loss - self.entry_price
                reward = self.entry_price - self.take_profit

            if risk > 0 and reward > 0:
                self.rr_ratio = round(reward / risk, 2)

        return self


class JournalEntryUpdate(BaseModel):
    """Payload for updating an existing journal entry."""

    symbol: str | None = Field(None, min_length=1, max_length=30)
    direction: Literal["BUY", "SELL"] | None = None
    volume: float | None = Field(None, gt=0.0)
    entry_price: float | None = Field(None, gt=0.0)
    exit_price: float | None = Field(None, gt=0.0)
    stop_loss: float | None = Field(None, gt=0.0)
    take_profit: float | None = Field(None, gt=0.0)
    gross_profit: float | None = None
    commission: float | None = None
    swap: float | None = None
    net_pnl: float | None = None
    risk_amount: float | None = Field(None, ge=0.0)
    risk_percentage: float | None = Field(None, ge=0.0)
    rr_ratio: float | None = Field(None, ge=0.0)
    open_time: datetime | None = None
    close_time: datetime | None = None
    status: Literal["OPEN", "CLOSED", "PARTIAL"] | None = None
    strategy_id: uuid.UUID | None = None
    setup_tag: str | None = Field(None, max_length=50)
    user_notes: str | None = None
    emotional_state: str | None = Field(None, max_length=50)


class JournalEntryResponse(BaseModel):
    """Complete journal entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    user_id: uuid.UUID
    broker_position_id: int | None = None
    symbol: str
    direction: str
    volume: float
    entry_price: float
    exit_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    gross_profit: float
    commission: float
    swap: float
    net_pnl: float
    risk_amount: float | None = None
    risk_percentage: float | None = None
    rr_ratio: float | None = None
    open_time: datetime
    close_time: datetime | None = None
    status: str
    session: str | None = None
    strategy_id: uuid.UUID | None = None
    setup_tag: str | None = None
    user_notes: str | None = None
    emotional_state: str | None = None
    idempotency_hash: str | None = None
    source: Literal["MT5", "CSV", "MANUAL"] = "MANUAL"
    created_at: datetime
    updated_at: datetime


class JournalListResponse(BaseModel):
    """Paginated response for journal entries list."""

    items: list[JournalEntryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CSVRowError(BaseModel):
    """Row-level validation error detail for CSV import."""

    row: int = Field(..., description="1-indexed row number in the CSV file")
    field: str = Field(..., description="Name of the column/field with the error")
    message: str = Field(..., description="Human-readable validation message")
    raw_value: str | None = Field(None, description="Sanitized original cell value")


class CSVPreviewResponse(BaseModel):
    """Dry-run preview response of a parsed CSV file."""

    total_rows: int = Field(..., description="Total data rows detected in CSV")
    valid_rows_count: int = Field(..., description="Number of valid, importable rows")
    error_rows_count: int = Field(..., description="Number of rows with validation errors")
    sample_valid_rows: list[dict[str, Any]] = Field(
        default_factory=list, description="Sample of up to 5 valid parsed trades"
    )
    errors: list[CSVRowError] = Field(default_factory=list, description="List of row errors")


class CSVImportResponse(BaseModel):
    """Outcome summary of a committed CSV import execution."""

    account_id: uuid.UUID
    total_rows: int
    imported_count: int
    duplicates_skipped: int
    error_rows_count: int
    errors: list[CSVRowError] = Field(default_factory=list)
