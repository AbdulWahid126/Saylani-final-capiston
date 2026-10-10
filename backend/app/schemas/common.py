from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class DataClassificationBadge(StrEnum):
    """Mandatory classification badges defined in RULES.md and DESIGN.md."""

    VERIFIED_DATA = "VERIFIED DATA"
    CALCULATED_METRICS = "CALCULATED METRICS"
    HISTORICAL_STATISTICS = "HISTORICAL STATISTICS"
    ML_ESTIMATES = "ML ESTIMATES"
    AI_INTERPRETATION = "AI INTERPRETATION"


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class StandardResponse(BaseModel):
    success: bool = True
    message: str | None = None
    classification: DataClassificationBadge | None = None
