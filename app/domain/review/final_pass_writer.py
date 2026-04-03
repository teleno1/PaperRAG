from __future__ import annotations

import json

from langchain_core.output_parsers import PydanticOutputParser

from app.core.config import get_settings
from app.domain.review.chapter_ops import (
    collapse_sections_to_paragraphs,
    is_abstract_title,
    is_summary_outlook_title,
    iter_sentences,
)
from app.domain.review.models import ChapterDraft, PlannedChapter, RetrievedSource
from app.domain.review.prompts import build_abstract_prompt, build_summary_outlook_prompt
from app.infrastructure.llm.clients import DeepSeekChatFactory


def _format_outlook_sources(sources: list[RetrievedSource]) -> str:
    payload = []
    for source in sources:
        payload.append(
            {
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
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _select_prompt(target_chapter: PlannedChapter):
    if is_abstract_title(target_chapter.chapter_title):
        return build_abstract_prompt(), True
    if is_summary_outlook_title(target_chapter.chapter_title):
        return build_summary_outlook_prompt(), False
    raise ValueError(f"Unsupported final-pass chapter title: {target_chapter.chapter_title}")


def write_final_pass_chapter(
    outline_summary: str,
    target_chapter: PlannedChapter,
    body_digest: str,
    supporting_sources: list[RetrievedSource] | None = None,
) -> ChapterDraft:
    parser = PydanticOutputParser(pydantic_object=ChapterDraft)
    llm = DeepSeekChatFactory().create(temperature=get_settings().pipeline.temperature_final_pass)
    prompt, expects_keywords = _select_prompt(target_chapter)

    target_meta = json.dumps(
        {
            "chapter_id": target_chapter.chapter_id,
            "chapter_title": target_chapter.chapter_title,
            "chapter_description": target_chapter.chapter_description,
            "query": target_chapter.query,
            "citation_policy": target_chapter.citation_policy,
            "write_stage": target_chapter.write_stage,
        },
        ensure_ascii=False,
        indent=2,
    )

    chain = prompt | llm | parser
    result = chain.invoke(
        {
            "format_instructions": parser.get_format_instructions(),
            "outline_summary": outline_summary,
            "target_meta": target_meta,
            "body_digest": body_digest,
            "outlook_sources_json": _format_outlook_sources(supporting_sources or []),
        }
    )
    result.chapter_id = target_chapter.chapter_id
    result.chapter_title = target_chapter.chapter_title
    collapse_sections_to_paragraphs(result)

    if expects_keywords:
        result.keywords = [keyword.strip() for keyword in result.keywords if keyword.strip()][:5]
    else:
        result.keywords = []

    for sentence in iter_sentences(result):
        sentence.cite_source_ids = []

    return result
