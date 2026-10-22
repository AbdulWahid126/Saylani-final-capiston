"""FastAPI endpoints for TASK-014: AI Chart Screenshot Analyzer (Vision).

Provides authenticated endpoints for:
- Uploading and analyzing chart screenshots using ICT, SMC, Price Action, or General modes.
- Retrieving past user chart analyses with strict multi-tenant ownership.
- Deleting chart analyses.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.vision import ChartAnalysisResponse, StrategyMode
from app.services.chart_analyzer import (
    analyze_chart_screenshot,
    delete_user_chart_analysis,
    get_user_chart_analysis,
    list_user_chart_analyses,
)

router = APIRouter(prefix="/vision", tags=["AI Chart Analyzer"])


@router.post(
    "/analyze",
    response_model=ChartAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze trading chart screenshot using vision AI",
)
async def analyze_chart(
    file: UploadFile = File(..., description="Chart screenshot image file (PNG, JPEG, WEBP)"),
    strategy_mode: StrategyMode = Form(
        StrategyMode.GENERAL, description="Analysis methodology framework"
    ),
    custom_prompt: str | None = Form(
        None, description="Optional custom questions or focus instructions"
    ),
    include_playbook: bool = Form(
        True, description="Cross-reference with personal playbook rules if available"
    ),
    persist: bool = Form(True, description="Persist analysis record in database history"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChartAnalysisResponse:
    """Accepts a chart image and generates structured technical observations with visual evidence and uncertainty."""
    file_bytes = await file.read()
    return await analyze_chart_screenshot(
        db=db,
        user_id=current_user.id,
        file_bytes=file_bytes,
        filename=file.filename,
        content_type=file.content_type,
        strategy_mode=strategy_mode,
        custom_prompt=custom_prompt,
        include_playbook=include_playbook,
        persist=persist,
    )


@router.get(
    "/analyses",
    response_model=list[ChartAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="List past chart analyses for current user",
)
async def list_analyses(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChartAnalysisResponse]:
    """Retrieves paginated historical chart analyses owned by current authenticated user."""
    return await list_user_chart_analyses(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/analyses/{analysis_id}",
    response_model=ChartAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve single chart analysis",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChartAnalysisResponse:
    """Retrieves details of a specific chart analysis owned by the current user."""
    return await get_user_chart_analysis(
        db=db,
        user_id=current_user.id,
        analysis_id=analysis_id,
    )


@router.delete(
    "/analyses/{analysis_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete chart analysis",
)
async def delete_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Deletes a chart analysis owned by the current user."""
    await delete_user_chart_analysis(
        db=db,
        user_id=current_user.id,
        analysis_id=analysis_id,
    )
    return {
        "message": "Chart analysis deleted successfully.",
        "id": str(analysis_id),
    }
