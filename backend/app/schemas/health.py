from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    status: Literal["healthy", "degraded", "disconnected"]
    latency_ms: float | None = None
    engine: str | None = None


class SystemHealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    service: str = "ai-trading-copilot-backend"
    version: str = "0.1.0"
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    database: DatabaseHealth
    mt5_terminal_detected: bool = False
