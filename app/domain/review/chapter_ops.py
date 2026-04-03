from __future__ import annotations

from collections.abc import Iterator

from app.domain.review.models import ChapterDraft, ParagraphDraft, SentenceDraft

ABSTRACT_TITLES = {"\u6458\u8981", "abstract"}
SUMMARY_OUTLOOK_TITLES = {
    "\u603b\u7ed3\u4e0e\u5c55\u671b",
    "summary and outlook",
    "\u7ed3\u8bed",
    "conclusion",
    "conclusion and outlook",
}


def is_abstract_title(title: str) -> bool:
    return title.strip().lower() in ABSTRACT_TITLES


def is_summary_outlook_title(title: str) -> bool:
    return title.strip().lower() in SUMMARY_OUTLOOK_TITLES


def iter_paragraphs(chapter: ChapterDraft) -> Iterator[ParagraphDraft]:
    yield from chapter.paragraphs
    for section in chapter.sections:
        yield from section.paragraphs


def iter_sentences(chapter: ChapterDraft) -> Iterator[SentenceDraft]:
    for paragraph in iter_paragraphs(chapter):
        yield from paragraph.sentences


def collapse_sections_to_paragraphs(chapter: ChapterDraft) -> ChapterDraft:
    if not chapter.sections:
        return chapter

    paragraphs = list(chapter.paragraphs)
    for section in chapter.sections:
        paragraphs.extend(section.paragraphs)

    chapter.paragraphs = paragraphs
    chapter.sections = []
    return chapter


def normalize_single_section_chapter(chapter: ChapterDraft) -> ChapterDraft:
    if len(chapter.sections) != 1:
        return chapter
    return collapse_sections_to_paragraphs(chapter)
