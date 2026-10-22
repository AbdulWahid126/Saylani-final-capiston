"""Document text extraction and semantic chunking service for Personal Playbook RAG.

Supports:
- Markdown (.md)
- Plain Text (.txt)
- Adobe PDF (.pdf) via pypdf

Enforces strict size limits, sanitizes filenames against path traversal,
handles corrupted files gracefully, and generates partitioned chunks with metadata.
"""

import io
import os
import re
from typing import Any

import pypdf

from app.core.config import settings
from app.core.errors import BadRequestError


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename against path traversal and unsafe characters."""
    base = os.path.basename(filename).strip()
    # Remove null bytes and control chars
    clean = re.sub(r"[\x00-\x1f\x7f]", "", base)
    # Replace unsafe characters
    clean = re.sub(r"[^\w\.\-\s]", "_", clean)
    clean = clean.strip()
    return clean or "unnamed_document.txt"


def extract_text_and_pages(filename: str, content_bytes: bytes) -> list[tuple[str, int | None]]:
    """Extracts text content and optional page numbers from raw file bytes.

    Returns:
        List of tuples: (page_text, page_number_or_none)
    """
    if not content_bytes:
        raise BadRequestError("Uploaded file is empty (0 bytes).")

    if len(content_bytes) > settings.MAX_DOCUMENT_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_DOCUMENT_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise BadRequestError(f"File size exceeds the maximum limit of {max_mb} MB.")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
        allowed_str = ", ".join(settings.ALLOWED_DOCUMENT_EXTENSIONS)
        raise BadRequestError(
            f"Unsupported file format '{ext}'. Supported formats are: {allowed_str}"
        )

    results: list[tuple[str, int | None]] = []

    if ext in [".txt", ".md"]:
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content_bytes.decode("latin-1")
            except Exception as exc:
                raise BadRequestError("Unable to decode text file. Ensure UTF-8 encoding.") from exc

        # Remove null bytes
        text = text.replace("\x00", "")
        if not text.strip():
            raise BadRequestError("File contains no readable text content.")
        results.append((text, None))

    elif ext == ".pdf":
        try:
            stream = io.BytesIO(content_bytes)
            reader = pypdf.PdfReader(stream)
            if reader.is_encrypted:
                raise BadRequestError(
                    "Password-protected PDF files cannot be processed. Please upload an unprotected document."
                )

            total_pages = len(reader.pages)
            if total_pages == 0:
                raise BadRequestError("PDF file contains no pages.")

            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                page_text = page_text.replace("\x00", "").strip()
                if page_text:
                    results.append((page_text, page_idx + 1))

            if not results:
                raise BadRequestError(
                    "PDF file contains no extractable text. Scanned image-only PDFs without OCR are not supported."
                )

        except BadRequestError:
            raise
        except Exception as exc:
            raise BadRequestError(f"Malformed or corrupted PDF file: {exc}") from exc

    return results


def chunk_document(
    pages: list[tuple[str, int | None]],
    filename: str,
    doc_type: str,
    chunk_size: int = 800,
    overlap: int = 100,
    max_chunks: int = 500,
) -> list[tuple[str, dict[str, Any]]]:
    """Partitions extracted document text into overlapping semantic segments.

    Returns:
        List of tuples: (chunk_text, chunk_metadata_dict)
    """
    if chunk_size <= overlap:
        chunk_size = overlap + 200

    chunks: list[tuple[str, dict[str, Any]]] = []
    chunk_index = 0

    for page_text, page_num in pages:
        text = page_text.strip()
        if not text:
            continue

        text_len = len(text)
        start = 0

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # If not at the end of the text, try to break at a paragraph or sentence boundary
            if end < text_len:
                boundary = -1
                for delim in ["\n\n", "\n", ". ", "? ", "! "]:
                    pos = text.rfind(delim, start + overlap, end)
                    if pos != -1:
                        boundary = pos + len(delim)
                        break
                if boundary != -1 and boundary > start:
                    end = boundary

            chunk_content = text[start:end].strip()
            if chunk_content:
                metadata: dict[str, Any] = {
                    "filename": filename,
                    "doc_type": doc_type,
                    "chunk_index": chunk_index,
                    "char_start": start,
                    "char_end": end,
                }
                if page_num is not None:
                    metadata["page"] = page_num

                chunks.append((chunk_content, metadata))
                chunk_index += 1

                if len(chunks) > max_chunks:
                    raise BadRequestError(
                        f"Document exceeds the maximum limit of {max_chunks} chunks. "
                        "Please split the document into smaller files."
                    )

            if end >= text_len:
                break
            start = max(start + 1, end - overlap)

    if not chunks:
        raise BadRequestError("Document could not be partitioned into readable chunks.")

    # Update total_chunks in each chunk's metadata
    total_c = len(chunks)
    for _, meta in chunks:
        meta["total_chunks"] = total_c

    return chunks
