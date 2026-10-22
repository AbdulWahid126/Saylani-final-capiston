"""Pydantic v2 schemas for Personal Playbook Knowledge Base (pgvector RAG).

Defines schemas for document ingestion, processing statuses, vector search,
source citations, and grounded question answering.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import DataClassificationBadge


class DocumentType(str, Enum):
    """Categorized document knowledge types."""

    PLAYBOOK = "PLAYBOOK"
    STRATEGY = "STRATEGY"
    CHECKLIST = "CHECKLIST"
    RULES = "RULES"
    NOTES = "NOTES"


class DocumentProcessingStatus(str, Enum):
    """Lifecycle status of an ingested knowledge base document."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentKnowledgeResponse(BaseModel):
    """Metadata response for a user-owned playbook knowledge document."""

    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    doc_type: str
    file_size: int
    status: DocumentProcessingStatus
    chunk_count: int
    error_message: str | None = None
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
    data_badge: DataClassificationBadge = Field(
        default=DataClassificationBadge.VERIFIED_DATA,
        description="Mandatory visual data distinction badge.",
    )


class DocumentListResponse(BaseModel):
    """Paginated list of user documents."""

    total: int
    items: list[DocumentKnowledgeResponse]
    data_badge: DataClassificationBadge = Field(
        default=DataClassificationBadge.VERIFIED_DATA,
        description="Mandatory visual data distinction badge.",
    )


class PlaybookSearchResultItem(BaseModel):
    """Individual retrieved text chunk with vector similarity score and citation."""

    chunk_id: str
    document_id: str
    document_filename: str
    doc_type: str
    content: str
    similarity: float = Field(ge=0.0, le=1.0)
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)


class PlaybookSearchRequest(BaseModel):
    """Request payload for semantic vector similarity search."""

    query: str = Field(
        min_length=1, max_length=1000, description="Search query or setup description."
    )
    doc_type: DocumentType | None = Field(
        default=None, description="Optional document type filter."
    )
    top_k: int = Field(
        default=4, ge=1, le=20, description="Maximum number of relevant chunks to retrieve."
    )
    similarity_threshold: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Minimum cosine similarity cutoff."
    )


class PlaybookSearchResponse(BaseModel):
    """Semantic vector search response containing matching chunks and citations."""

    query: str
    total_results: int
    results: list[PlaybookSearchResultItem]
    data_badge: DataClassificationBadge = Field(
        default=DataClassificationBadge.CALCULATED_METRICS,
        description="Mandatory visual data distinction badge.",
    )


class PlaybookCitation(BaseModel):
    """Exact source citation linking an answer statement to a retrieved document passage."""

    document_id: str
    document_filename: str
    chunk_id: str
    page: int | None = None
    chunk_index: int
    similarity: float = Field(ge=0.0, le=1.0)
    text_snippet: str


class PlaybookAskRequest(BaseModel):
    """Request payload for asking a question grounded in user's playbook documents."""

    question: str = Field(min_length=3, max_length=1000, description="Trading question to answer.")
    doc_type: DocumentType | None = Field(
        default=None, description="Optional document type filter."
    )
    top_k: int = Field(
        default=4, ge=1, le=10, description="Maximum chunks to retrieve for context."
    )
    similarity_threshold: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Minimum cosine similarity threshold."
    )


class PlaybookAskResponse(BaseModel):
    """Evidence-grounded RAG response with source citations and confidence rating."""

    question: str
    answer: str
    has_sufficient_context: bool
    citations: list[PlaybookCitation]
    confidence_score: float = Field(ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)
    data_badge: DataClassificationBadge = Field(
        default=DataClassificationBadge.AI_INTERPRETATION,
        description="Mandatory visual data distinction badge.",
    )
