from __future__ import annotations

import re
from pathlib import Path

from app.domain.models import ParsedDocument, ParsedDocumentUnit

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


class MarkdownParser:
    source_type = "markdown"
    supported_extensions = (".md", ".markdown")

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        lines = source_path.read_text(encoding="utf-8").splitlines()
        units: list[ParsedDocumentUnit] = []
        current_section: str | None = None
        current_heading_level: int | None = None
        buffer: list[str] = []

        def flush_buffer() -> None:
            content = "\n".join(buffer).strip()
            if not content:
                return
            metadata: dict[str, int] = {}
            if current_heading_level is not None:
                metadata["heading_level"] = current_heading_level
            units.append(
                ParsedDocumentUnit(
                    content=content,
                    section=current_section,
                    metadata=metadata,
                )
            )

        for raw_line in lines:
            line = raw_line.rstrip()
            heading_match = HEADING_PATTERN.match(line)
            if heading_match:
                flush_buffer()
                current_section = heading_match.group(2).strip()
                current_heading_level = len(heading_match.group(1))
                buffer = []
                continue

            stripped = line.strip()
            if not stripped:
                if buffer and buffer[-1] != "":
                    buffer.append("")
                continue
            buffer.append(stripped)

        flush_buffer()

        return ParsedDocument(
            document_id=document_id or source_path.stem,
            source_path=str(source_path),
            source_type=self.source_type,
            units=units,
            metadata={"parser": self.source_type},
        )
