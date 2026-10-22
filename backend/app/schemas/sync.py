import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SyncRequest(BaseModel):
    """Payload schema for triggering an account deal synchronization."""

    days: int = Field(
        30, ge=1, le=730, description="Number of historical days to synchronize (default: 30)"
    )
    date_from: datetime | None = Field(None, description="Optional explicit start timestamp (UTC)")
    date_to: datetime | None = Field(None, description="Optional explicit end timestamp (UTC)")

    @model_validator(mode="after")
    def validate_date_bounds(self) -> "SyncRequest":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from cannot be greater than date_to")
        return self


class SyncSummaryResponse(BaseModel):
    """Execution summary returned following a deal synchronization run."""

    model_config = ConfigDict(from_attributes=True)

    account_id: uuid.UUID
    total_deals_retrieved: int = Field(
        ..., description="Total raw deals fetched from terminal for the date range"
    )
    new_deals_saved: int = Field(..., description="Number of newly inserted unique raw deals")
    positions_aggregated: int = Field(
        ..., description="Total distinct position lifecycles processed"
    )
    open_positions_count: int = Field(
        ..., description="Positions currently open or partially closed"
    )
    closed_positions_count: int = Field(..., description="Positions completely closed")
    sync_status: str = Field(..., description="Account sync status after synchronization")
    synced_at: datetime = Field(..., description="Completion timestamp (UTC)")
