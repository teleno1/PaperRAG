from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol

from app.core.exceptions import UnsupportedDocumentTypeError
from app.domain.models import ParsedDocument


class DocumentParser(Protocol):
    source_type: str
    supported_extensions: tuple[str, ...]

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        """Parse a document into normalized units."""


def _normalize_extensions(extensions: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for extension in extensions:
        cleaned = extension.strip().lower()
        if not cleaned:
            raise ValueError("supported extension must not be empty")
        if not cleaned.startswith("."):
            cleaned = f".{cleaned}"
        normalized.append(cleaned)
    if not normalized:
        raise ValueError("supported_extensions must not be empty")
    return tuple(dict.fromkeys(normalized))


class ParserRegistry:
    def __init__(self, parsers: Iterable[DocumentParser]) -> None:
        self._parsers = list(parsers)
        if not self._parsers:
            raise ValueError("at least one parser is required")
        self._extensions_by_parser = {
            id(parser): _normalize_extensions(parser.supported_extensions) for parser in self._parsers
        }

    def supported_extensions(self) -> list[str]:
        seen: dict[str, None] = {}
        for parser in self._parsers:
            for extension in self._extensions_by_parser[id(parser)]:
                seen.setdefault(extension, None)
        return list(seen.keys())

    def select_parser(self, source_path: Path) -> DocumentParser:
        suffix = source_path.suffix.lower()
        for parser in self._parsers:
            if suffix in self._extensions_by_parser[id(parser)]:
                return parser
        raise UnsupportedDocumentTypeError(
            source_path=str(source_path),
            supported_extensions=self.supported_extensions(),
        )

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        parser = self.select_parser(source_path)
        return parser.parse(source_path, document_id=document_id)
