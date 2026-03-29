from __future__ import annotations

import json

from langchain_core.output_parsers import PydanticOutputParser

from app.core.config import get_settings
from app.domain.review.models import ChapterDraft, PlannedChapter
from app.domain.review.prompts import build_final_pass_prompt
from app.infrastructure.llm.clients import DeepSeekChatFactory


def write_final_pass_chapter(
    outline_summary: str,
    target_chapter: PlannedChapter,
    body_digest: str,
) -> ChapterDraft:
    parser = PydanticOutputParser(pydantic_object=ChapterDraft)
    llm = DeepSeekChatFactory().create(temperature=get_settings().pipeline.temperature_final_pass)
    prompt = build_final_pass_prompt()

    target_meta = json.dumps(
        {
            "chapter_id": target_chapter.chapter_id,
            "chapter_title": target_chapter.chapter_title,
            "chapter_description": target_chapter.chapter_description,
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
        }
    )
    result.chapter_id = target_chapter.chapter_id
    result.chapter_title = target_chapter.chapter_title

    for section in result.sections:
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                sentence.cite_source_ids = []

    return result

