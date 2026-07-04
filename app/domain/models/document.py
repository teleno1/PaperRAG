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


@dataclass(slots=True)
class ParsedDocumentUnit:
    content: str
    section: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.content = _require_text(self.content, "content")
        self.section = self._normalize_optional_text(self.section, "section")
        self.page_number = self._normalize_page_number(self.page_number)
        self.metadata = _copy_metadata(self.metadata)

    @staticmethod
    def _normalize_optional_text(value: str | None, field_name: str) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be empty")
        return normalized

    @staticmethod
    def _normalize_page_number(value: int | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("page_number must be an int")
        if value < 1:
            raise ValueError("page_number must be greater than or equal to 1")
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "section": self.section,
            "page_number": self.page_number,
            "metadata": _copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ParsedDocumentUnit:
        return cls(
            content=_require_payload_text(payload, "content"),
            section=payload.get("section"),
            page_number=payload.get("page_number"),
            metadata=_copy_metadata(payload.get("metadata", {})),
        )


@dataclass(slots=True)
class ParsedDocument:
    document_id: str
    source_path: str
    source_type: str
    units: list[ParsedDocumentUnit] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.document_id = _require_text(self.document_id, "document_id")
        self.source_path = _require_text(self.source_path, "source_path")
        self.source_type = _require_text(self.source_type, "source_type").lower()
        self.units = self._copy_units(self.units)
        self.metadata = _copy_metadata(self.metadata)

    @staticmethod
    def _copy_units(units: list[ParsedDocumentUnit]) -> list[ParsedDocumentUnit]:
        copied_units: list[ParsedDocumentUnit] = []
        for unit in units:
            if not isinstance(unit, ParsedDocumentUnit):
                raise ValueError("units must contain ParsedDocumentUnit instances")
            copied_units.append(unit)
        return copied_units

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "units": [unit.to_dict() for unit in self.units],
            "metadata": _copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ParsedDocument:
        raw_units = payload.get("units", [])
        if not isinstance(raw_units, list):
            raise ValueError("units must be a list")
        for unit in raw_units:
            if not isinstance(unit, dict):
                raise ValueError("units must contain dict items")
        return cls(
            document_id=_require_payload_text(payload, "document_id"),
            source_path=_require_payload_text(payload, "source_path"),
            source_type=_require_payload_text(payload, "source_type"),
            units=[ParsedDocumentUnit.from_dict(unit) for unit in raw_units],
            metadata=_copy_metadata(payload.get("metadata", {})),
        )
