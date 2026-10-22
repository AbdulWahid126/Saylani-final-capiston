"""FastAPI endpoints for TASK-015: Beginner Learning Hub & Curated Resource Discovery.

Provides authenticated endpoints for:
- Retrieving curriculum categories
- Listing and filtering lessons by category, difficulty, or search term
- Retrieving individual lessons with detailed curriculum content
- Listing, filtering, and paginating curated educational resources
- Retrieving individual vetted educational resources
"""

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.learning import (
    CostClassification,
    CuratedResourceListResponse,
    CuratedResourceResponse,
    CurriculumCategoryResponse,
    CurriculumLessonDetail,
    CurriculumLessonListResponse,
    DifficultyLevel,
    ResourceType,
)
from app.services.learning_service import LearningService, get_learning_service

router = APIRouter(prefix="/learning", tags=["Learning Hub"])


@router.get(
    "/categories",
    response_model=list[CurriculumCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve all curriculum categories",
)
async def get_curriculum_categories(
    current_user: User = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> list[CurriculumCategoryResponse]:
    """Retrieve the full list of curriculum categories ordered sequentially."""
    return service.get_categories()


@router.get(
    "/lessons",
    response_model=CurriculumLessonListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter curriculum lessons",
)
async def list_lessons(
    category_id: str | None = Query(
        None, description="Filter by category slug (e.g. 'forex-fundamentals')"
    ),
    difficulty: DifficultyLevel | None = Query(None, description="Filter by difficulty level"),
    search: str | None = Query(
        None, description="Case-insensitive search across title, description, and terms"
    ),
    current_user: User = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> CurriculumLessonListResponse:
    """Retrieve curriculum lesson summaries with optional filtering by category, difficulty, and search."""
    lessons = service.get_lessons(category_id=category_id, difficulty=difficulty, search=search)
    return CurriculumLessonListResponse(items=lessons, total=len(lessons))


@router.get(
    "/lessons/{lesson_id_or_slug}",
    response_model=CurriculumLessonDetail,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific lesson by ID or slug",
)
async def get_lesson_detail(
    lesson_id_or_slug: str,
    current_user: User = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> CurriculumLessonDetail:
    """Retrieve full educational lesson content including objectives, key terms, example, pitfalls, and recap."""
    lesson = service.get_lesson_by_id_or_slug(lesson_id_or_slug)
    if not lesson:
        raise NotFoundError(f"Curriculum lesson '{lesson_id_or_slug}' not found")
    return lesson


@router.get(
    "/resources",
    response_model=CuratedResourceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List, filter, and paginate curated educational resources",
)
async def list_resources(
    topic: str | None = Query(None, description="Filter by topic keyword"),
    difficulty: DifficultyLevel | None = Query(None, description="Filter by target difficulty"),
    cost: CostClassification | None = Query(None, description="Filter by free or paid status"),
    resource_type: ResourceType | None = Query(
        None, description="Filter by format type (article, book, etc.)"
    ),
    language: str | None = Query(None, description="Filter by language code (default 'en')"),
    search: str | None = Query(None, description="Search across title, publisher, and description"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    current_user: User = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> CuratedResourceListResponse:
    """Retrieve paginated, vetted educational resources with multi-attribute filtering."""
    items, total, total_pages = service.get_resources(
        topic=topic,
        difficulty=difficulty,
        cost=cost,
        resource_type=resource_type,
        language=language,
        search=search,
        page=page,
        page_size=page_size,
    )
    return CuratedResourceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/resources/{resource_id}",
    response_model=CuratedResourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific curated resource by ID",
)
async def get_resource_detail(
    resource_id: str,
    current_user: User = Depends(get_current_user),
    service: LearningService = Depends(get_learning_service),
) -> CuratedResourceResponse:
    """Retrieve details for a single vetted educational resource."""
    resource = service.get_resource_by_id(resource_id)
    if not resource:
        raise NotFoundError(f"Educational resource '{resource_id}' not found")
    return resource
