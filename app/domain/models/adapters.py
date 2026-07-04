from __future__ import annotations

from typing import Any

from app.domain.models.chunk import Chunk
from app.domain.models.document import DocumentChunk, DocumentMetadata, Source
from app.domain.models.paper_metadata import PaperMetadata

LEGACY_SOURCE_TYPE = "pdf"


def _legacy_metadata(
    *,
    title: str,
    authors: list[str],
    year: str,
    venue: str,
    extra_metadata: dict[str, Any] | None = None,
    paper_id: str | None = None,
) -> dict[str, Any]:
    metadata = dict(extra_metadata or {})
    metadata.update(
        {
        "title": title,
        "authors": list(authors),
        "year": year,
        "venue": venue,
        }
    )
    if paper_id:
        metadata["paper_id"] = paper_id
    return metadata


def _resolve_document_id(document_id: str | None, paper_id: str | None) -> str:
    if document_id:
        return document_id
    if paper_id:
        return paper_id
    raise ValueError("document_id or paper_id is required")


def _default_chunk_id(document_id: str, chunk_index: int) -> str:
    return f"{document_id}__chunk_{chunk_index:04d}"


def paper_metadata_to_document_metadata(
    paper_metadata: PaperMetadata,
    *,
    source_path: str,
    source_type: str = LEGACY_SOURCE_TYPE,
    document_id: str | None = None,
    paper_id: str | None = None,
    section: str = "UNKNOWN",
    extra_metadata: dict[str, Any] | None = None,
) -> DocumentMetadata:
    resolved_document_id = _resolve_document_id(document_id, paper_id)
    return DocumentMetadata(
        document_id=resolved_document_id,
        source_path=source_path,
        source_type=source_type,
        section=section,
        metadata=_legacy_metadata(
            title=paper_metadata.title,
            authors=paper_metadata.authors,
            year=paper_metadata.year,
            venue=paper_metadata.venue,
            extra_metadata=extra_metadata,
            paper_id=paper_id or resolved_document_id,
        ),
    )


def paper_metadata_to_source(
    paper_metadata: PaperMetadata,
    *,
    source_path: str,
    source_type: str = LEGACY_SOURCE_TYPE,
    source_id: str | None = None,
    document_id: str | None = None,
    paper_id: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> Source:
    resolved_document_id = _resolve_document_id(document_id, paper_id)
    return Source(
        source_id=source_id or resolved_document_id,
        source_path=source_path,
        source_type=source_type,
        metadata=_legacy_metadata(
            title=paper_metadata.title,
            authors=paper_metadata.authors,
            year=paper_metadata.year,
            venue=paper_metadata.venue,
            extra_metadata=extra_metadata,
            paper_id=paper_id or resolved_document_id,
        ),
    )


def chunk_to_document_chunk(
    chunk: Chunk,
    *,
    source_path: str,
    source_type: str = LEGACY_SOURCE_TYPE,
    document_id: str | None = None,
    paper_id: str | None = None,
    chunk_id: str | None = None,
    chunk_index: int | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> DocumentChunk:
    resolved_document_id = _resolve_document_id(document_id, paper_id)
    if chunk_id is None and chunk_index is None:
        raise ValueError("chunk_id or chunk_index is required")
    return DocumentChunk(
        chunk_id=chunk_id or _default_chunk_id(resolved_document_id, chunk_index),
        document_id=resolved_document_id,
        source_path=source_path,
        source_type=source_type,
        section=chunk.section or "UNKNOWN",
        content=chunk.content,
        metadata=_legacy_metadata(
            title=chunk.title,
            authors=chunk.authors,
            year=chunk.year,
            venue=chunk.venue,
            extra_metadata=extra_metadata,
            paper_id=paper_id or resolved_document_id,
        ),
    )
