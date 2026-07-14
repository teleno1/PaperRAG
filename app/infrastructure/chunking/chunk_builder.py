from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.domain.models.chunk import Chunk, SourceAnchor
from app.domain.models.paper_metadata import PaperMetadata
from app.infrastructure.chunking.metadata_extractor import MetadataExtractor

MAX_TOKENS = 500
OVERLAP_SENTENCES = 2
MIN_UNIT_LEN = 50
CHUNKING_VERSION = "chunking-v1"


@dataclass(slots=True)
class _Unit:
    text: str
    section: str
    page_number: int | None = None
    character_start: int | None = None
    character_end: int | None = None


@dataclass(slots=True)
class _Sentence:
    text: str
    section: str
    page_number: int | None
    character_start: int | None
    character_end: int | None


class ChunkBuilder:
    """Create bounded, section-safe chunks while retaining source locations."""

    def __init__(
        self,
        metadata_extractor: MetadataExtractor | None = None,
        *,
        max_tokens: int = MAX_TOKENS,
        overlap_sentences: int = OVERLAP_SENTENCES,
        min_unit_len: int = MIN_UNIT_LEN,
    ) -> None:
        self._metadata_extractor = metadata_extractor or MetadataExtractor()
        self._max_tokens = max_tokens
        self._overlap_sentences = overlap_sentences
        self._min_unit_len = min_unit_len

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def overlap_sentences(self) -> int:
        return self._overlap_sentences

    @property
    def min_unit_len(self) -> int:
        return self._min_unit_len

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(text.strip().split())

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        chinese_chars = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        total_chars = len(text)
        if chinese_chars > 0:
            return int(chinese_chars / 1.5 + (total_chars - chinese_chars) / 4)
        return max(1, total_chars // 4)

    @staticmethod
    def _split_into_sentence_spans(text: str) -> list[tuple[int, int]]:
        """Split Chinese and English prose without requiring whitespace."""

        spans: list[tuple[int, int]] = []
        start = 0
        for index, character in enumerate(text):
            if character not in ".!?。！？；;":
                continue
            next_character = text[index + 1] if index + 1 < len(text) else ""
            is_boundary = character in "。！？；;" or not next_character or next_character.isspace()
            if not is_boundary:
                continue
            end = index + 1
            if text[start:end].strip():
                spans.append((start, end))
            start = end
        if text[start:].strip():
            spans.append((start, len(text)))
        return spans or ([(0, len(text))] if text.strip() else [])

    @classmethod
    def _sentences_for_unit(cls, unit: _Unit) -> list[_Sentence]:
        result: list[_Sentence] = []
        for local_start, local_end in cls._split_into_sentence_spans(unit.text):
            sentence = cls._clean_text(unit.text[local_start:local_end])
            if not sentence:
                continue
            character_start = (
                unit.character_start + local_start
                if unit.character_start is not None
                else None
            )
            character_end = (
                unit.character_end
                if local_end == len(unit.text) and unit.character_end is not None
                else unit.character_start + local_end
                if unit.character_start is not None
                else unit.character_end
            )
            result.append(
                _Sentence(
                    text=sentence,
                    section=unit.section,
                    page_number=unit.page_number,
                    character_start=character_start,
                    character_end=character_end,
                )
            )
        return result

    @staticmethod
    def _extract_text_from_title(block: dict[str, Any]) -> str:
        return " ".join(
            item["content"] for item in block["content"]["title_content"] if item["type"] == "text"
        )

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
                    results.append("- " + self._clean_text(content["content"]))
        return results

    def _json_to_units(self, data: list[Any]) -> list[_Unit]:
        units: list[_Unit] = []
        current_section = "UNKNOWN"
        character_cursor = 0
        for page_number, page in enumerate(data, start=1):
            for block in page:
                block_type = block["type"]
                if block_type.startswith("page_"):
                    continue
                if block_type in {"image", "table", "equation_inline", "equation_interline"}:
                    continue
                if block_type == "title":
                    title = self._extract_text_from_title(block).strip()
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
                    texts = []
                for text in texts:
                    if not text:
                        continue
                    start = character_cursor
                    end = start + len(text)
                    units.append(
                        _Unit(
                            text=text,
                            section=current_section,
                            page_number=page_number,
                            character_start=start,
                            character_end=end,
                        )
                    )
                    character_cursor = end + 1
        return units

    def _merge_small_units(self, units: list[_Unit]) -> list[_Unit]:
        merged: list[_Unit] = []
        buffer: _Unit | None = None
        for unit in units:
            if buffer is None:
                buffer = unit
                continue
            if (
                unit.section == buffer.section
                and unit.page_number == buffer.page_number
                and self._estimate_tokens(buffer.text) < self._min_unit_len
            ):
                separator = " "
                buffer.text += separator + unit.text
                buffer.character_end = unit.character_end
                buffer.page_number = unit.page_number or buffer.page_number
            else:
                merged.append(buffer)
                buffer = unit
        if buffer:
            merged.append(buffer)
        return merged

    @staticmethod
    def _parsed_unit_offsets(unit: ParsedDocumentUnit, cursor: int) -> tuple[int, int]:
        raw_start = unit.metadata.get("character_start")
        raw_end = unit.metadata.get("character_end")
        start = raw_start if isinstance(raw_start, int) and raw_start >= 0 else cursor
        end = raw_end if isinstance(raw_end, int) and raw_end >= start else start + len(unit.content)
        return start, end

    def _units_from_parsed_document(self, parsed_document: ParsedDocument) -> list[_Unit]:
        units: list[_Unit] = []
        cursor = 0
        for unit in parsed_document.units:
            if not unit.content.strip():
                continue
            start, end = self._parsed_unit_offsets(unit, cursor)
            units.append(
                _Unit(
                    text=unit.content,
                    section=unit.section or "UNKNOWN",
                    page_number=unit.page_number,
                    character_start=start,
                    character_end=end,
                )
            )
            cursor = end + 1
        return units

    def _make_chunk(
        self,
        sentences: list[_Sentence],
        metadata: PaperMetadata,
        *,
        document_version_id: str | None,
        source_path: str | None,
        parser: str | None,
        parser_version: str | None,
    ) -> Chunk:
        section = sentences[0].section
        excerpt = " ".join(sentence.text for sentence in sentences).strip()
        pages = [sentence.page_number for sentence in sentences if sentence.page_number is not None]
        starts = [sentence.character_start for sentence in sentences if sentence.character_start is not None]
        ends = [sentence.character_end for sentence in sentences if sentence.character_end is not None]
        anchor = None
        if document_version_id and source_path:
            anchor = SourceAnchor(
                document_version_id=document_version_id,
                source_path=source_path,
                page_start=min(pages) if pages else None,
                page_end=max(pages) if pages else None,
                character_start=min(starts) if starts else None,
                character_end=max(ends) if ends else None,
                section=section,
                excerpt=excerpt,
                parser=parser or "unknown",
                parser_version=parser_version,
                chunking_version=CHUNKING_VERSION,
            )
        return Chunk(
            content=f"[Title: {metadata.title}]\n[Section: {section}]\n{excerpt}",
            excerpt=excerpt,
            section=section,
            title=metadata.title,
            authors=metadata.authors,
            year=metadata.year,
            venue=metadata.venue,
            page_start=min(pages) if pages else None,
            page_end=max(pages) if pages else None,
            character_start=min(starts) if starts else None,
            character_end=max(ends) if ends else None,
            source_anchor=anchor,
        )

    def _build_chunks(
        self,
        units: list[_Unit],
        metadata: PaperMetadata,
        *,
        document_version_id: str | None = None,
        source_path: str | None = None,
        parser: str | None = None,
        parser_version: str | None = None,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        current_sentences: list[_Sentence] = []
        current_section: str | None = None
        for unit in units:
            if current_section is not None and unit.section != current_section:
                if current_sentences:
                    chunks.append(
                        self._make_chunk(
                            current_sentences,
                            metadata,
                            document_version_id=document_version_id,
                            source_path=source_path,
                            parser=parser,
                            parser_version=parser_version,
                        )
                    )
                current_sentences = []
                current_section = unit.section
            if current_section is None:
                current_section = unit.section

            for sentence in self._sentences_for_unit(unit):
                candidate = " ".join(item.text for item in current_sentences + [sentence])
                if current_sentences and self._estimate_tokens(candidate) > self._max_tokens:
                    chunks.append(
                        self._make_chunk(
                            current_sentences,
                            metadata,
                            document_version_id=document_version_id,
                            source_path=source_path,
                            parser=parser,
                            parser_version=parser_version,
                        )
                    )
                    current_sentences = current_sentences[-self._overlap_sentences :]
                current_sentences.append(sentence)

        if current_sentences:
            chunks.append(
                self._make_chunk(
                    current_sentences,
                    metadata,
                    document_version_id=document_version_id,
                    source_path=source_path,
                    parser=parser,
                    parser_version=parser_version,
                )
            )
        return chunks

    @staticmethod
    def _parsed_document_metadata(parsed_document: ParsedDocument) -> PaperMetadata:
        raw_metadata = parsed_document.metadata
        authors = raw_metadata.get("authors", [])
        return PaperMetadata(
            title=str(raw_metadata.get("title") or parsed_document.document_id),
            authors=[str(item) for item in authors] if isinstance(authors, list) else [],
            year=str(raw_metadata.get("year") or ""),
            venue=str(raw_metadata.get("venue") or ""),
        )

    def build_chunks_from_parsed_document(self, parsed_document: ParsedDocument) -> list[Chunk]:
        metadata = self._parsed_document_metadata(parsed_document)
        return self._build_chunks(
            self._units_from_parsed_document(parsed_document),
            metadata,
            document_version_id=parsed_document.document_id,
            source_path=parsed_document.source_path,
            parser=str(parsed_document.metadata.get("parser") or parsed_document.source_type),
            parser_version=(
                str(parsed_document.metadata["parser_version"])
                if parsed_document.metadata.get("parser_version") is not None
                else None
            ),
        )

    def build_chunks(self, mineru_json_path: Path) -> list[Chunk]:
        with mineru_json_path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
        metadata = self._metadata_extractor.extract(data)
        return self._build_chunks(
            self._merge_small_units(self._json_to_units(data)),
            metadata,
            document_version_id=mineru_json_path.parent.name,
            source_path=str(mineru_json_path),
            parser="mineru",
        )
