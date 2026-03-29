from __future__ import annotations

import json

from langchain_core.output_parsers import PydanticOutputParser

from app.core.config import get_settings
from app.domain.review.models import ChapterBundle, ChapterDraft
from app.domain.review.prompts import build_chapter_writer_prompt
from app.infrastructure.llm.clients import DeepSeekChatFactory


def _json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _format_chapter_meta(bundle: ChapterBundle) -> str:
    return _json_dumps(
        {
            "chapter_id": bundle.chapter_id,
            "chapter_title": bundle.chapter_title,
            "chapter_description": bundle.chapter_description,
            "chapter_query": bundle.chapter_query,
            "chapter_citation_policy": bundle.chapter_citation_policy,
        }
    )


def _format_leaf_sections(bundle: ChapterBundle) -> str:
    payload = []
    for section in bundle.leaf_sections:
        payload.append(
            {
                "section_id": section.section_id,
                "section_title": section.section_title,
                "section_description": section.section_description,
                "section_query": section.section_query,
                "citation_policy": section.citation_policy,
                "source_ids": section.source_ids,
            }
        )
    return _json_dumps(payload)


def _format_unique_sources(bundle: ChapterBundle) -> str:
    payload = []
    for source in bundle.unique_sources:
        payload.append(
            {
                "source_id": source.source_id,
                "paper_id": source.paper_id,
                "chunk_id": source.chunk_id,
                "title": source.title,
                "authors": source.authors,
                "year": source.year,
                "venue": source.venue,
                "section": source.section,
                "content": source.content,
            }
        )
    return _json_dumps(payload)


def write_chapter(
    outline_summary: str,
    bundle: ChapterBundle,
    previous_recap: str = "",
    citation_snapshot: dict | None = None,
) -> ChapterDraft:
    parser = PydanticOutputParser(pydantic_object=ChapterDraft)
    llm = DeepSeekChatFactory().create(temperature=get_settings().pipeline.temperature_chapter)
    prompt = build_chapter_writer_prompt()
    citation_snapshot = citation_snapshot or {}

    chain = prompt | llm | parser
    result = chain.invoke(
        {
            "format_instructions": parser.get_format_instructions(),
            "outline_summary": outline_summary,
            "chapter_meta": _format_chapter_meta(bundle),
            "leaf_sections_json": _format_leaf_sections(bundle),
            "unique_sources_json": _format_unique_sources(bundle),
            "previous_recap": previous_recap or "无",
            "citation_snapshot": _json_dumps(citation_snapshot),
        }
    )
    result.chapter_id = bundle.chapter_id
    result.chapter_title = bundle.chapter_title
    return result

