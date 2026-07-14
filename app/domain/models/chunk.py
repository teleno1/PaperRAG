from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceAnchor:
    """Stable, serializable location metadata for one indexed chunk."""

    document_version_id: str
    source_path: str
    excerpt: str
    section: str = ""
    page_start: int | None = None
    page_end: int | None = None
    character_start: int | None = None
    character_end: int | None = None
    parser: str = ""
    parser_version: str | None = None
    chunking_version: str = "chunking-v1"

    def __post_init__(self) -> None:
        self.document_version_id = self.document_version_id.strip()
        self.source_path = self.source_path.strip()
        self.excerpt = self.excerpt.strip()
        self.section = self.section.strip()
        self.parser = self.parser.strip()
        if not self.document_version_id:
            raise ValueError("source anchor document_version_id must not be empty")
        if not self.source_path:
            raise ValueError("source anchor source_path must not be empty")
        if not self.excerpt:
            raise ValueError("source anchor excerpt must not be empty")
        if self.page_start is not None and self.page_start < 1:
            raise ValueError("source anchor page_start must be greater than or equal to 1")
        if self.page_end is not None and self.page_end < 1:
            raise ValueError("source anchor page_end must be greater than or equal to 1")
        if self.page_start is not None and self.page_end is not None and self.page_end < self.page_start:
            raise ValueError("source anchor page_end must not precede page_start")
        if self.character_start is not None and self.character_start < 0:
            raise ValueError("source anchor character_start must not be negative")
        if self.character_end is not None and self.character_end < 0:
            raise ValueError("source anchor character_end must not be negative")
        if self.character_start is not None and self.character_end is not None and self.character_end < self.character_start:
            raise ValueError("source anchor character_end must not precede character_start")

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_version_id": self.document_version_id,
            "source_path": self.source_path,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "character_start": self.character_start,
            "character_end": self.character_end,
            "section": self.section,
            "excerpt": self.excerpt,
            "parser": self.parser,
            "parser_version": self.parser_version,
            "chunking_version": self.chunking_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceAnchor":
        return cls(
            document_version_id=str(payload["document_version_id"]),
            source_path=str(payload["source_path"]),
            excerpt=str(payload["excerpt"]),
            section=str(payload.get("section") or ""),
            page_start=payload.get("page_start"),
            page_end=payload.get("page_end"),
            character_start=payload.get("character_start"),
            character_end=payload.get("character_end"),
            parser=str(payload.get("parser") or ""),
            parser_version=payload.get("parser_version"),
            chunking_version=str(payload.get("chunking_version") or "chunking-v1"),
        )


@dataclass(slots=True)
class Chunk:
    content: str
    section: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    excerpt: str = ""
    page_start: int | None = None
    page_end: int | None = None
    character_start: int | None = None
    character_end: int | None = None
    source_anchor: SourceAnchor | None = None

