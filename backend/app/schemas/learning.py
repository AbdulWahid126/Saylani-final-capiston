"""Pydantic schemas for the Beginner Learning Hub & Curated Resource Discovery.

Adheres to Pydantic v2 conventions and strict typing.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DifficultyLevel(StrEnum):
    """Educational difficulty level."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class CostClassification(StrEnum):
    """Cost classification for educational resources."""

    FREE = "free"
    PAID = "paid"


class ResourceType(StrEnum):
    """Type of learning material."""

    ARTICLE = "article"
    VIDEO = "video"
    COURSE = "course"
    BOOK = "book"
    DOCUMENTATION = "documentation"


class KeyTermItem(BaseModel):
    """Definition of a specific trading term."""

    model_config = ConfigDict(frozen=True)

    term: str = Field(..., description="The trading term or acronym")
    definition: str = Field(..., description="Clear, objective definition")


class HypotheticalExample(BaseModel):
    """Hypothetical trading or risk calculation example."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., description="Example title")
    scenario: str = Field(..., description="Context and assumed parameters (clearly hypothetical)")
    calculation: str = Field(..., description="Deterministic mathematical calculation")
    outcome: str = Field(..., description="Result of the calculation")
    key_takeaway: str = Field(..., description="Core lesson derived from this scenario")
    badge: str = Field(default="[HYPOTHETICAL EXAMPLE]", description="Mandatory distinction badge")


class CurriculumCategoryResponse(BaseModel):
    """Top-level curriculum category summary."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique slug identifier (e.g., 'forex-fundamentals')")
    title: str = Field(..., description="Category display title")
    short_description: str = Field(..., description="Brief overview of what is taught")
    icon: str = Field(..., description="Suggested UI icon identifier")
    lesson_count: int = Field(default=0, description="Total number of lessons in this category")
    order: int = Field(..., description="Display order sequence")


class CurriculumLessonSummary(BaseModel):
    """Summary of a single educational lesson for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique lesson ID")
    slug: str = Field(..., description="URL-friendly slug")
    title: str = Field(..., description="Lesson title")
    category_id: str = Field(..., description="Parent category identifier")
    category_title: str = Field(..., description="Parent category title")
    short_description: str = Field(..., description="Beginner-friendly summary of the lesson")
    difficulty: DifficultyLevel = Field(..., description="Difficulty level")
    estimated_minutes: int = Field(..., description="Estimated reading / study time in minutes")
    prerequisites: list[str] = Field(
        default_factory=list, description="IDs of recommended prerequisite lessons"
    )
    badge: str = Field(
        default="[EDUCATIONAL CONTENT]", description="Mandatory classification badge"
    )


class CurriculumLessonDetail(CurriculumLessonSummary):
    """Full lesson content including objectives, key terms, example, pitfalls, and recap."""

    learning_objectives: list[str] = Field(
        ..., description="Specific, measurable learning objectives"
    )
    key_terms: list[KeyTermItem] = Field(
        default_factory=list, description="Glossary of relevant terms"
    )
    content_markdown: str = Field(
        ..., description="In-depth educational content formatted in Markdown"
    )
    hypothetical_example: HypotheticalExample | None = Field(
        None, description="Deterministic hypothetical calculation or scenario"
    )
    common_mistakes: list[str] = Field(
        default_factory=list, description="Common beginner pitfalls to avoid"
    )
    recap: str = Field(..., description="Concise closing summary")
    disclaimer: str = Field(
        default=(
            "EDUCATIONAL NOTICE: This lesson is provided solely for educational and informational purposes. "
            "It does not constitute financial, investment, or trading advice. Trading foreign exchange and "
            "leveraged derivatives carries substantial risk of capital loss. Past results and hypothetical examples "
            "are not indicative of future performance."
        ),
        description="Mandatory legal and regulatory disclaimer",
    )


class CurriculumLessonListResponse(BaseModel):
    """Response schema for listing curriculum lessons."""

    items: list[CurriculumLessonSummary] = Field(..., description="List of lesson summaries")
    total: int = Field(..., description="Total count matching filter criteria")


class CuratedResourceResponse(BaseModel):
    """Vetted external or reference educational resource."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique resource identifier")
    title: str = Field(..., description="Resource title")
    publisher: str = Field(..., description="Author, publisher, or issuing institution")
    topic: str = Field(..., description="Trading topic or subject area")
    difficulty: DifficultyLevel = Field(..., description="Target proficiency level")
    cost: CostClassification = Field(..., description="Free vs Paid classification")
    resource_type: ResourceType = Field(..., description="Format of the resource")
    url: HttpUrl = Field(..., description="Official, verified web address")
    description: str = Field(..., description="Objective, neutral summary of the resource")
    language: str = Field(default="en", description="Resource language code")
    verified: bool = Field(
        default=True, description="Whether the link and content have been verified"
    )
    last_reviewed: str = Field(..., description="Date of last content review (YYYY-MM-DD)")
    badge: str = Field(default="[VERIFIED RESOURCE]", description="Visual distinction badge")


class CuratedResourceListResponse(BaseModel):
    """Paginated response for curated educational resources."""

    items: list[CuratedResourceResponse] = Field(
        ..., description="List of resources for the current page"
    )
    total: int = Field(..., description="Total count of matching resources")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of available pages")
