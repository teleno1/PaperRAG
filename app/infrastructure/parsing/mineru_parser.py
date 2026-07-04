from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.paths import PathManager, get_paths
from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.infrastructure.parsing.mineru_client import MinerUClient

SKIPPED_BLOCK_TYPES = {"image", "table", "equation_inline", "equation_interline"}


class MinerUParser:
    source_type = "pdf"
    supported_extensions = (".pdf",)

    def __init__(
        self,
        mineru_client: MinerUClient | None = None,
        output_root: Path | None = None,
        paths: PathManager | None = None,
    ) -> None:
        self._mineru_client = mineru_client or MinerUClient()
        self._output_root = output_root
        self._paths = paths

    @staticmethod
    def _clean_text(text: str) -> str:
        return text.strip().replace("\n", " ")

    def _extract_text_from_title(self, block: dict[str, Any]) -> str:
        return " ".join(item["content"] for item in block["content"]["title_content"] if item["type"] == "text").strip()

    def _extract_text_from_paragraph(self, block: dict[str, Any]) -> list[str]:
        return [
            self._clean_text(item["content"])
            for item in block["content"]["paragraph_content"]
            if item["type"] == "text" and self._clean_text(item["content"])
        ]

    def _extract_text_from_text(self, block: dict[str, Any]) -> str:
        return self._clean_text(str(block["content"]))

    def _extract_text_from_list(self, block: dict[str, Any]) -> list[str]:
        if block["content"]["list_type"] != "text_list":
            return []
        results: list[str] = []
        for item in block["content"]["list_items"]:
            for content in item["item_content"]:
                if content["type"] == "text":
                    cleaned = self._clean_text(content["content"])
                    if cleaned:
                        results.append(f"- {cleaned}")
        return results

    def _parse_units(self, data: list[Any]) -> list[ParsedDocumentUnit]:
        units: list[ParsedDocumentUnit] = []
        current_section = "UNKNOWN"

        for page_number, page in enumerate(data, start=1):
            for block in page:
                block_type = block["type"]
                if block_type.startswith("page_") or block_type in SKIPPED_BLOCK_TYPES:
                    continue
                if block_type == "title":
                    title = self._extract_text_from_title(block)
                    if title:
                        current_section = title
                    continue
                if block_type == "paragraph":
                    texts = self._extract_text_from_paragraph(block)
                elif block_type == "text":
                    texts = [self._extract_text_from_text(block)]
                elif block_type == "list":
                    texts = self._extract_text_from_list(block)
                else:
                    continue

                for text in texts:
                    if not text:
                        continue
                    units.append(
                        ParsedDocumentUnit(
                            content=text,
                            section=current_section,
                            page_number=page_number,
                            metadata={"block_type": block_type},
                        )
                    )
        return units

    def _resolve_output_dir(self, source_path: Path) -> Path:
        base_dir = self._output_root or (self._paths or get_paths()).processed_dir
        return base_dir / source_path.stem

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        output_dir = self._resolve_output_dir(source_path)
        self._mineru_client.parse_pdf(pdf_path=source_path, output_dir=output_dir)
        content_path = output_dir / "content_list_v2.json"
        with content_path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)

        return ParsedDocument(
            document_id=document_id or source_path.stem,
            source_path=str(source_path),
            source_type=self.source_type,
            units=self._parse_units(data),
            metadata={
                "parser": "mineru",
                "mineru_output_dir": str(output_dir),
            },
        )
