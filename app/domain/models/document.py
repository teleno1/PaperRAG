from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _require_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _require_payload_text(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _copy_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dict")
    return dict(metadata)


@dataclass(slots=True)
class Source:
    source_id: str
    source_path: str
    source_type: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source_id = _require_text(self.source_id, "source_id")
        self.source_path = _require_text(self.source_path, "source_path")
        self.source_type = _require_text(self.source_type, "source_type").lower()
        self.metadata = _copy_metadata(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "metadata": _copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Source:
        return cls(
            source_id=_require_payload_text(payload, "source_id"),
            source_path=_require_payload_text(payload, "source_path"),
            source_type=_require_payload_text(payload, "source_type"),
            metadata=_copy_metadata(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class DocumentMetadata:
    document_id: str
    source_path: str
    source_type: str
    section: str = "UNKNOWN"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.document_id = _require_text(self.document_id, "document_id")
        self.source_path = _require_text(self.source_path, "source_path")
        self.source_type = _require_text(self.source_type, "source_type").lower()
        self.section = _require_text(self.section, "section")
        self.metadata = _copy_metadata(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "section": self.section,
            "metadata": _copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DocumentMetadata:
        return cls(
            document_id=_require_payload_text(payload, "document_id"),
            source_path=_require_payload_text(payload, "source_path"),
            source_type=_require_payload_text(payload, "source_type"),
            section=_require_payload_text({"section": payload.get("section", "UNKNOWN")}, "section"),
            metadata=_copy_metadata(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    source_path: str
    source_type: str
    section: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.chunk_id = _require_text(self.chunk_id, "chunk_id")
        self.document_id = _require_text(self.document_id, "document_id")
        self.source_path = _require_text(self.source_path, "source_path")
        self.source_type = _require_text(self.source_type, "source_type").lower()
        self.section = _require_text(self.section, "section")
        self.content = _require_text(self.content, "content")
        self.metadata = _copy_metadata(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "section": self.section,
            "content": self.content,
            "metadata": _copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DocumentChunk:
        return cls(
            chunk_id=_require_payload_text(payload, "chunk_id"),
            document_id=_require_payload_text(payload, "document_id"),
            source_path=_require_payload_text(payload, "source_path"),
            source_type=_require_payload_text(payload, "source_type"),
            section=_require_payload_text(payload, "section"),
            content=_require_payload_text(payload, "content"),
            metadata=_copy_metadata(payload.get("metadata", {})),
        )
