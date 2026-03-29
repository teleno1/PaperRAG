from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.models.chunk import Chunk
from app.domain.models.paper_metadata import PaperMetadata
from app.infrastructure.chunking.metadata_extractor import MetadataExtractor

MAX_TOKENS = 500
OVERLAP_SENTENCES = 2
MIN_UNIT_LEN = 50


class ChunkBuilder:
    def __init__(self, metadata_extractor: MetadataExtractor | None = None) -> None:
        self._metadata_extractor = metadata_extractor or MetadataExtractor()

    @staticmethod
    def _clean_text(text: str) -> str:
        return text.strip().replace("\n", " ")

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        total_chars = len(text)
        if chinese_chars > 0:
            return int(chinese_chars / 1.5 + (total_chars - chinese_chars) / 4)
        return total_chars // 4

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        return [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]

    def _extract_text_from_title(self, block: dict) -> str:
        return " ".join(item["content"] for item in block["content"]["title_content"] if item["type"] == "text")

    def _extract_text_from_paragraph(self, block: dict) -> list[str]:
        return [self._clean_text(item["content"]) for item in block["content"]["paragraph_content"] if item["type"] == "text"]

    def _extract_text_from_text(self, block: dict) -> str:
        return self._clean_text(block["content"])

    def _extract_text_from_list(self, block: dict) -> list[str]:
        if block["content"]["list_type"] != "text_list":
            return []
        results: list[str] = []
        for item in block["content"]["list_items"]:
            for content in item["item_content"]:
                if content["type"] == "text":
                    results.append("- " + self._clean_text(content["content"]))
        return results

    def _json_to_units(self, data: list) -> list[dict[str, str]]:
        units: list[dict[str, str]] = []
        current_section = "UNKNOWN"
        for page in data:
            for block in page:
                block_type = block["type"]
                if block_type.startswith("page_"):
                    continue
                if block_type in {"image", "table", "equation_inline", "equation_interline"}:
                    continue
                if block_type == "title":
                    current_section = self._extract_text_from_title(block)
                    continue
                if block_type == "paragraph":
                    for text in self._extract_text_from_paragraph(block):
                        units.append({"text": text, "section": current_section})
                elif block_type == "text":
                    units.append({"text": self._extract_text_from_text(block), "section": current_section})
                elif block_type == "list":
                    for text in self._extract_text_from_list(block):
                        units.append({"text": text, "section": current_section})
        return units

    def _merge_small_units(self, units: list[dict[str, str]]) -> list[dict[str, str]]:
        merged: list[dict[str, str]] = []
        buffer: dict[str, str] | None = None
        for unit in units:
            if buffer is None:
                buffer = unit
                continue
            if unit["section"] == buffer["section"] and self._estimate_tokens(buffer["text"]) < MIN_UNIT_LEN:
                buffer["text"] += " " + unit["text"]
            else:
                merged.append(buffer)
                buffer = unit
        if buffer:
            merged.append(buffer)
        return merged

    def _make_chunk(self, sentences: list[str], section: str, metadata: PaperMetadata) -> Chunk:
        content = " ".join(sentences).strip()
        return Chunk(
            content=f"[Title: {metadata.title}]\n[Section: {section}]\n{content}",
            section=section,
            title=metadata.title,
            authors=metadata.authors,
            year=metadata.year,
            venue=metadata.venue,
        )

    def _build_chunks(self, units: list[dict[str, str]], metadata: PaperMetadata) -> list[Chunk]:
        chunks: list[Chunk] = []
        current_sentences: list[str] = []
        current_section: str | None = None
        for unit in units:
            section = unit["section"]
            sentences = self._split_into_sentences(unit["text"])
            if current_section is not None and section != current_section:
                if current_sentences:
                    chunks.append(self._make_chunk(current_sentences, current_section, metadata))
                current_sentences = []
                current_section = section
            if current_section is None:
                current_section = section

            for sentence in sentences:
                candidate = " ".join(current_sentences + [sentence])
                if current_sentences and self._estimate_tokens(candidate) > MAX_TOKENS:
                    chunks.append(self._make_chunk(current_sentences, current_section, metadata))
                    current_sentences = current_sentences[-OVERLAP_SENTENCES:]
                current_sentences.append(sentence)

        if current_sentences and current_section is not None:
            chunks.append(self._make_chunk(current_sentences, current_section, metadata))
        return chunks

    def build_chunks(self, mineru_json_path: Path) -> list[Chunk]:
        with mineru_json_path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
        metadata = self._metadata_extractor.extract(data)
        units = self._merge_small_units(self._json_to_units(data))
        return self._build_chunks(units, metadata)
