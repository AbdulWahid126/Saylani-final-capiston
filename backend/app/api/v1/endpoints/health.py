import time
from os import path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import DatabaseHealth, SystemHealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=SystemHealthResponse)
async def check_health(db: AsyncSession = Depends(get_db)) -> SystemHealthResponse:
    """System health check endpoint verifying database connectivity and environment status."""
    start_time = time.perf_counter()
    db_status = "healthy"
    engine_name = db.bind.dialect.name if db.bind else "unknown"

    try:
        await db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    except Exception:
        db_status = "disconnected"
        latency_ms = None

    # Check local MT5 terminal installation status
    mt5_present = path.exists(settings.MT5_TERMINAL_PATH)

    system_status = "healthy"
    if db_status != "healthy":
        system_status = "degraded"

    return SystemHealthResponse(
        status=system_status,
        service="ai-trading-copilot-backend",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=DatabaseHealth(
            status=db_status,
            latency_ms=latency_ms,
            engine=engine_name,
        ),
        mt5_terminal_detected=mt5_present,
    )
