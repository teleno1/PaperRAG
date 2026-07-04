from __future__ import annotations

from pathlib import Path

from app.domain.models import ParsedDocument, ParsedDocumentUnit


class TxtParser:
    source_type = "txt"
    supported_extensions = (".txt",)

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        text = source_path.read_text(encoding="utf-8").strip()
        units: list[ParsedDocumentUnit] = []
        if text:
            units.append(
                ParsedDocumentUnit(
                    content=text,
                    metadata={"line_count": len(text.splitlines())},
                )
            )
        return ParsedDocument(
            document_id=document_id or source_path.stem,
            source_path=str(source_path),
            source_type=self.source_type,
            units=units,
            metadata={"parser": self.source_type},
        )
