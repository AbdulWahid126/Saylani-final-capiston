"""Service layer for the Beginner Learning Hub & Curated Resource Discovery.

Provides deterministic search, filtering, and retrieval for:
- Curriculum categories
- Structured educational lessons
- Curated, vetted external resources
"""

import math

from app.learning_data.content import (
    CURATED_RESOURCES,
    CURRICULUM_CATEGORIES,
    CURRICULUM_LESSONS,
)
from app.schemas.learning import (
    CostClassification,
    CuratedResourceResponse,
    CurriculumCategoryResponse,
    CurriculumLessonDetail,
    CurriculumLessonSummary,
    DifficultyLevel,
    ResourceType,
)


class LearningService:
    """In-memory service providing fast, deterministic educational content discovery."""

    def __init__(
        self,
        categories: list[CurriculumCategoryResponse] | None = None,
        lessons: list[CurriculumLessonDetail] | None = None,
        resources: list[CuratedResourceResponse] | None = None,
    ) -> None:
        self._categories = categories if categories is not None else list(CURRICULUM_CATEGORIES)
        self._lessons = lessons if lessons is not None else list(CURRICULUM_LESSONS)
        self._resources = resources if resources is not None else list(CURATED_RESOURCES)

    def get_categories(self) -> list[CurriculumCategoryResponse]:
        """Retrieve all curriculum categories ordered by sequence."""
        # Dynamically ensure lesson_count reflects current lessons in memory
        category_counts: dict[str, int] = {}
        for lesson in self._lessons:
            category_counts[lesson.category_id] = category_counts.get(lesson.category_id, 0) + 1

        result: list[CurriculumCategoryResponse] = []
        for cat in sorted(self._categories, key=lambda c: c.order):
            updated_cat = CurriculumCategoryResponse(
                id=cat.id,
                title=cat.title,
                short_description=cat.short_description,
                icon=cat.icon,
                lesson_count=category_counts.get(cat.id, cat.lesson_count),
                order=cat.order,
            )
            result.append(updated_cat)
        return result

    def get_lessons(
        self,
        category_id: str | None = None,
        difficulty: DifficultyLevel | None = None,
        search: str | None = None,
    ) -> list[CurriculumLessonSummary]:
        """Filter and search educational lessons."""
        filtered: list[CurriculumLessonDetail] = self._lessons

        if category_id:
            cat_clean = category_id.strip().lower()
            filtered = [lesson for lesson in filtered if lesson.category_id.lower() == cat_clean]

        if difficulty:
            filtered = [lesson for lesson in filtered if lesson.difficulty == difficulty]

        if search:
            query = search.strip().lower()
            matching: list[CurriculumLessonDetail] = []
            for lesson in filtered:
                in_title = query in lesson.title.lower()
                in_desc = query in lesson.short_description.lower()
                in_terms = any(
                    query in term.term.lower() or query in term.definition.lower()
                    for term in lesson.key_terms
                )
                if in_title or in_desc or in_terms:
                    matching.append(lesson)
            filtered = matching

        # Map details to summaries for list response
        return [
            CurriculumLessonSummary(
                id=lesson.id,
                slug=lesson.slug,
                title=lesson.title,
                category_id=lesson.category_id,
                category_title=lesson.category_title,
                short_description=lesson.short_description,
                difficulty=lesson.difficulty,
                estimated_minutes=lesson.estimated_minutes,
                prerequisites=lesson.prerequisites,
                badge=lesson.badge,
            )
            for lesson in filtered
        ]

    def get_lesson_by_id_or_slug(self, identifier: str) -> CurriculumLessonDetail | None:
        """Find a single lesson by unique ID or URL slug."""
        clean_id = identifier.strip().lower()
        for lesson in self._lessons:
            if lesson.id.lower() == clean_id or lesson.slug.lower() == clean_id:
                return lesson
        return None

    def get_resources(
        self,
        topic: str | None = None,
        difficulty: DifficultyLevel | None = None,
        cost: CostClassification | None = None,
        resource_type: ResourceType | None = None,
        language: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[CuratedResourceResponse], int, int]:
        """Filter, search, and paginate curated educational resources.

        Returns:
            tuple of (paginated_items, total_count, total_pages)
        """
        filtered: list[CuratedResourceResponse] = self._resources

        if topic:
            topic_clean = topic.strip().lower()
            filtered = [r for r in filtered if topic_clean in r.topic.lower()]

        if difficulty:
            filtered = [r for r in filtered if r.difficulty == difficulty]

        if cost:
            filtered = [r for r in filtered if r.cost == cost]

        if resource_type:
            filtered = [r for r in filtered if r.resource_type == resource_type]

        if language:
            lang_clean = language.strip().lower()
            filtered = [r for r in filtered if r.language.lower() == lang_clean]

        if search:
            query = search.strip().lower()
            matching: list[CuratedResourceResponse] = []
            for r in filtered:
                in_title = query in r.title.lower()
                in_pub = query in r.publisher.lower()
                in_desc = query in r.description.lower()
                in_topic = query in r.topic.lower()
                if in_title or in_pub or in_desc or in_topic:
                    matching.append(r)
            filtered = matching

        total_count = len(filtered)
        if total_count == 0:
            return [], 0, 0

        total_pages = math.ceil(total_count / page_size)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = filtered[start_idx:end_idx]

        return paginated_items, total_count, total_pages

    def get_resource_by_id(self, resource_id: str) -> CuratedResourceResponse | None:
        """Find a single resource by unique identifier."""
        clean_id = resource_id.strip().lower()
        for res in self._resources:
            if res.id.lower() == clean_id:
                return res
        return None


# Global singleton instance for injection
_learning_service_instance: LearningService | None = None


def get_learning_service() -> LearningService:
    """Dependency provider for LearningService."""
    global _learning_service_instance
    if _learning_service_instance is None:
        _learning_service_instance = LearningService()
    return _learning_service_instance
