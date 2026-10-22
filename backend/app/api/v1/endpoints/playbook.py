"""Authenticated API endpoints for Personal Playbook Knowledge Base (pgvector RAG).

Implements:
- Document upload, text extraction, semantic chunking, and embedding generation
- Document listing, metadata retrieval, and deletion with cascading chunk cleanup
- Semantic vector similarity search filtered by authenticated user tenancy
- Grounded RAG question answering with exact citations and prompt-injection safeguards
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_resource_ownership, get_current_user
from app.core.config import settings
from app.core.errors import BadRequestError, NotFoundError
from app.db.session import get_db
from app.models.knowledge import DocumentChunk, DocumentKnowledge
from app.models.user import User
from app.schemas.common import DataClassificationBadge
from app.schemas.playbook import (
    DocumentKnowledgeResponse,
    DocumentListResponse,
    DocumentProcessingStatus,
    DocumentType,
    PlaybookAskRequest,
    PlaybookAskResponse,
    PlaybookSearchRequest,
    PlaybookSearchResponse,
)
from app.services.document_parser import (
    chunk_document,
    extract_text_and_pages,
    sanitize_filename,
)
from app.services.embedding_service import get_embedding_provider
from app.services.rag_engine import ask_playbook, search_playbook_chunks

router = APIRouter(prefix="/playbook", tags=["Playbook RAG"])


def _doc_to_response(doc: DocumentKnowledge) -> DocumentKnowledgeResponse:
    """Converts a DocumentKnowledge ORM entity to its validated response schema."""
    return DocumentKnowledgeResponse(
        id=doc.id,
        user_id=doc.user_id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        file_size=doc.file_size,
        status=DocumentProcessingStatus(doc.status),
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        uploaded_at=doc.uploaded_at,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        data_badge=DataClassificationBadge.VERIFIED_DATA,
    )


# ==============================================================================
# DOCUMENT MANAGEMENT ENDPOINTS
# ==============================================================================


@router.post(
    "/documents",
    response_model=DocumentKnowledgeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a trading playbook document",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (.txt, .md, .pdf)"),
    doc_type: DocumentType = Form(
        default=DocumentType.PLAYBOOK, description="Document categorization"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentKnowledgeResponse:
    """Uploads, parses, chunks, and vector-indexes a personal trading playbook document."""
    # 1. Enforce user document capacity limit
    user_doc_count_stmt = select(func.count(DocumentKnowledge.id)).where(
        DocumentKnowledge.user_id == current_user.id
    )
    current_doc_count = await db.scalar(user_doc_count_stmt) or 0
    if current_doc_count >= settings.MAX_DOCUMENTS_PER_USER:
        raise BadRequestError(
            f"Maximum document limit ({settings.MAX_DOCUMENTS_PER_USER}) reached. "
            "Please delete older documents before uploading new ones."
        )

    # 2. Read and validate raw file bytes
    content_bytes = await file.read()
    raw_filename = file.filename or "uploaded_playbook.txt"
    clean_filename = sanitize_filename(raw_filename)

    # 3. Parse text and extract pages
    pages = extract_text_and_pages(clean_filename, content_bytes)

    # 4. Chunk document into semantic passages
    chunks_data = chunk_document(
        pages=pages,
        filename=clean_filename,
        doc_type=doc_type.value,
        chunk_size=settings.RAG_CHUNK_SIZE_CHARS,
        overlap=settings.RAG_CHUNK_OVERLAP_CHARS,
        max_chunks=settings.MAX_CHUNKS_PER_DOCUMENT,
    )

    # 5. Extract texts for batch embedding generation
    chunk_texts = [content for content, _ in chunks_data]
    embedder = get_embedding_provider()

    doc_id = uuid.uuid4()
    now_utc = datetime.now(UTC)

    try:
        embeddings = await embedder.embed_texts(chunk_texts)
        if len(embeddings) != len(chunks_data):
            raise BadRequestError("Embedding count mismatch during vectorization.")
        doc_status = DocumentProcessingStatus.COMPLETED
        error_msg = None
    except Exception as exc:
        if settings.is_production:
            # In production, do not create partial broken documents
            raise BadRequestError(f"Embedding generation failed: {exc}") from exc
        # In non-production, record failure state if allowed
        doc_status = DocumentProcessingStatus.FAILED
        error_msg = str(exc)
        embeddings = [None] * len(chunks_data)

    # 6. Persist DocumentKnowledge header record
    doc_record = DocumentKnowledge(
        id=doc_id,
        user_id=current_user.id,
        filename=clean_filename,
        doc_type=doc_type.value,
        file_size=len(content_bytes),
        status=doc_status.value,
        chunk_count=len(chunks_data) if doc_status == DocumentProcessingStatus.COMPLETED else 0,
        error_message=error_msg,
        uploaded_at=now_utc,
    )
    db.add(doc_record)
    await db.flush()

    # 7. Persist DocumentChunks if embeddings were generated successfully
    if doc_status == DocumentProcessingStatus.COMPLETED:
        for (content, metadata), emb in zip(chunks_data, embeddings, strict=True):
            chunk_rec = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_id,
                user_id=current_user.id,
                content=content,
                embedding=emb,
                chunk_metadata=metadata,
            )
            db.add(chunk_rec)

    await db.commit()
    await db.refresh(doc_record)

    return _doc_to_response(doc_record)


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all uploaded playbook documents for the authenticated user",
)
async def list_documents(
    doc_type: DocumentType | None = Query(default=None, description="Filter by document type"),
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """Lists user-owned playbook knowledge documents with pagination and status."""
    base_query = select(DocumentKnowledge).where(DocumentKnowledge.user_id == current_user.id)
    if doc_type:
        base_query = base_query.where(DocumentKnowledge.doc_type == doc_type.value)

    count_stmt = select(func.count(DocumentKnowledge.id)).where(
        DocumentKnowledge.user_id == current_user.id
    )
    if doc_type:
        count_stmt = count_stmt.where(DocumentKnowledge.doc_type == doc_type.value)
    total = await db.scalar(count_stmt) or 0

    items_stmt = base_query.order_by(DocumentKnowledge.uploaded_at.desc()).offset(skip).limit(limit)
    docs = list((await db.scalars(items_stmt)).all())

    return DocumentListResponse(
        total=total,
        items=[_doc_to_response(d) for d in docs],
        data_badge=DataClassificationBadge.VERIFIED_DATA,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentKnowledgeResponse,
    summary="Get document metadata by ID",
)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentKnowledgeResponse:
    """Retrieves document metadata, validating tenant ownership."""
    stmt = select(DocumentKnowledge).where(DocumentKnowledge.id == document_id)
    doc = await db.scalar(stmt)
    if not doc:
        raise NotFoundError("DocumentKnowledge", document_id)
    enforce_resource_ownership(doc.user_id, current_user)

    return _doc_to_response(doc)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and its retrievable chunks",
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a document and cascades to remove all associated semantic vector chunks."""
    stmt = select(DocumentKnowledge).where(DocumentKnowledge.id == document_id)
    doc = await db.scalar(stmt)
    if not doc:
        raise NotFoundError("DocumentKnowledge", document_id)
    enforce_resource_ownership(doc.user_id, current_user)

    # Deleting document cascades delete to document_chunks due to ForeignKey ondelete='CASCADE'
    await db.delete(doc)
    await db.commit()


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=DocumentKnowledgeResponse,
    summary="Reprocess or re-embed an existing document's chunks",
)
async def reprocess_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentKnowledgeResponse:
    """Re-generates vector embeddings for all existing chunks in the specified document."""
    stmt = select(DocumentKnowledge).where(DocumentKnowledge.id == document_id)
    doc = await db.scalar(stmt)
    if not doc:
        raise NotFoundError("DocumentKnowledge", document_id)
    enforce_resource_ownership(doc.user_id, current_user)

    # Fetch existing chunks
    chunks_stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    chunks = list((await db.scalars(chunks_stmt)).all())

    if not chunks:
        doc.status = DocumentProcessingStatus.FAILED.value
        doc.error_message = "No chunks found to reprocess."
        await db.commit()
        await db.refresh(doc)
        return _doc_to_response(doc)

    texts = [c.content for c in chunks]
    embedder = get_embedding_provider()
    embeddings = await embedder.embed_texts(texts)

    for chunk, emb in zip(chunks, embeddings, strict=True):
        chunk.embedding = emb

    doc.status = DocumentProcessingStatus.COMPLETED.value
    doc.error_message = None
    doc.chunk_count = len(chunks)
    await db.commit()
    await db.refresh(doc)

    return _doc_to_response(doc)


# ==============================================================================
# RAG SEARCH & QUESTION ANSWERING ENDPOINTS
# ==============================================================================


@router.post(
    "/search",
    response_model=PlaybookSearchResponse,
    summary="Semantic vector search across personal playbook chunks",
)
async def search_playbook(
    payload: PlaybookSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaybookSearchResponse:
    """Executes pgvector semantic search over authenticated user's playbook chunks."""
    results = await search_playbook_chunks(
        db=db,
        user_id=current_user.id,
        query=payload.query,
        doc_type=payload.doc_type.value if payload.doc_type else None,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
    )

    return PlaybookSearchResponse(
        query=payload.query,
        total_results=len(results),
        results=results,
        data_badge=DataClassificationBadge.CALCULATED_METRICS,
    )


@router.post(
    "/ask",
    response_model=PlaybookAskResponse,
    summary="Ask a question grounded in personal playbook documents",
)
async def ask_playbook_question(
    payload: PlaybookAskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaybookAskResponse:
    """Generates an evidence-grounded answer with source citations from retrieved playbook chunks."""
    return await ask_playbook(
        db=db,
        user_id=current_user.id,
        question=payload.question,
        doc_type=payload.doc_type.value if payload.doc_type else None,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
    )
