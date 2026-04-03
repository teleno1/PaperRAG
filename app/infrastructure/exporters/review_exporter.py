from __future__ import annotations

import json
from pathlib import Path

from app.domain.review.chapter_ops import is_abstract_title
from app.domain.review.models import ChapterDraft, CitationRegistry, ExecutionPlan, ReferenceEntry, SourceRegistry

EXPORT_TEXT_FILENAME = "final_review.txt"
EXPORT_MD_FILENAME = "final_review.md"
EXPORT_JSON_FILENAME = "final_review.json"
REFERENCES_JSON_FILENAME = "references.json"


def sentence_to_text(sentence, citation_registry: CitationRegistry, source_registry: SourceRegistry) -> str:
    paper_ids: list[str] = []
    seen: set[str] = set()
    for source_id in sentence.cite_source_ids:
        paper_id = source_registry.source_id_to_paper_id.get(source_id)
        if paper_id and paper_id not in seen:
            seen.add(paper_id)
            paper_ids.append(paper_id)

    ref_nos: list[int] = []
    for paper_id in paper_ids:
        ref_no = citation_registry.paper_id_to_ref_no.get(paper_id)
        if ref_no is not None:
            ref_nos.append(ref_no)

    text = sentence.text.strip()
    if ref_nos:
        text += "[" + ",".join(str(item) for item in sorted(set(ref_nos))) + "]"
    return text


def _paragraph_to_text(paragraph, citation_registry: CitationRegistry, source_registry: SourceRegistry) -> str:
    return "".join(
        sentence_to_text(sentence, citation_registry, source_registry)
        for sentence in paragraph.sentences
    ).strip()


def _keywords_line(chapter: ChapterDraft) -> str:
    return f"\u5173\u952e\u8bcd\uff1a{'\uff1b'.join(chapter.keywords)}" if chapter.keywords else ""


def chapter_to_plain_text(
    chapter: ChapterDraft,
    citation_registry: CitationRegistry,
    source_registry: SourceRegistry,
) -> str:
    lines = [chapter.chapter_title]

    if chapter.paragraphs:
        for paragraph in chapter.paragraphs:
            paragraph_text = _paragraph_to_text(paragraph, citation_registry, source_registry)
            if paragraph_text:
                lines.append(paragraph_text)
        keyword_line = _keywords_line(chapter) if is_abstract_title(chapter.chapter_title) else ""
        if keyword_line:
            lines.append(keyword_line)
        return "\n".join(lines).strip()

    for section in chapter.sections:
        lines.append(section.section_title)
        for paragraph in section.paragraphs:
            paragraph_text = _paragraph_to_text(paragraph, citation_registry, source_registry)
            if paragraph_text:
                lines.append(paragraph_text)
        lines.append("")
    return "\n".join(lines).strip()


def chapter_to_markdown(
    chapter: ChapterDraft,
    citation_registry: CitationRegistry,
    source_registry: SourceRegistry,
) -> str:
    lines = [f"# {chapter.chapter_title}"]

    if chapter.paragraphs:
        for paragraph in chapter.paragraphs:
            paragraph_text = _paragraph_to_text(paragraph, citation_registry, source_registry)
            if paragraph_text:
                lines.append(paragraph_text)
                lines.append("")
        keyword_line = _keywords_line(chapter) if is_abstract_title(chapter.chapter_title) else ""
        if keyword_line:
            lines.append(keyword_line)
        return "\n".join(lines).strip()

    for section in chapter.sections:
        lines.append(f"## {section.section_title}")
        for paragraph in section.paragraphs:
            paragraph_text = _paragraph_to_text(paragraph, citation_registry, source_registry)
            if paragraph_text:
                lines.append(paragraph_text)
                lines.append("")
    return "\n".join(lines).strip()


def format_reference(reference: ReferenceEntry) -> str:
    authors = ", ".join(reference.authors) if reference.authors else "Unknown"
    parts = [f"[{reference.ref_no}] {authors}. {reference.title}"]
    if reference.venue:
        parts.append(reference.venue)
    if reference.year:
        parts.append(reference.year)
    return ". ".join(part.strip(". ") for part in parts if part) + "."


def export_all(
    plan: ExecutionPlan,
    body_drafts: list[ChapterDraft],
    final_drafts: list[ChapterDraft],
    citation_registry: CitationRegistry,
    source_registry: SourceRegistry,
    output_dir: str | Path,
) -> None:
    root = Path(output_dir)
    export_dir = root / "07_export"
    export_dir.mkdir(parents=True, exist_ok=True)

    body_map = {draft.chapter_id: draft for draft in body_drafts}
    final_map = {draft.chapter_id: draft for draft in final_drafts}

    ordered_blocks: list[ChapterDraft] = []
    for chapter in plan.final_pass_chapters:
        if is_abstract_title(chapter.chapter_title) and chapter.chapter_id in final_map:
            ordered_blocks.append(final_map[chapter.chapter_id])
    for chapter in plan.body_chapters:
        if chapter.chapter_id in body_map:
            ordered_blocks.append(body_map[chapter.chapter_id])
    for chapter in plan.final_pass_chapters:
        if not is_abstract_title(chapter.chapter_title) and chapter.chapter_id in final_map:
            ordered_blocks.append(final_map[chapter.chapter_id])

    ordered_text_blocks = [chapter_to_plain_text(chapter, citation_registry, source_registry) for chapter in ordered_blocks]
    ordered_md_blocks = [chapter_to_markdown(chapter, citation_registry, source_registry) for chapter in ordered_blocks]

    references_text = "\n".join(format_reference(reference) for reference in citation_registry.references)
    final_text = "\n\n".join(block for block in ordered_text_blocks if block.strip())
    final_md = "\n\n".join(block for block in ordered_md_blocks if block.strip())

    if references_text:
        final_text += "\n\n\u53c2\u8003\u6587\u732e\n" + references_text
        final_md += "\n\n# \u53c2\u8003\u6587\u732e\n" + references_text

    aggregated = {
        "title": plan.title,
        "language": plan.language,
        "body_chapters": [draft.model_dump() for draft in body_drafts],
        "final_pass_chapters": [draft.model_dump() for draft in final_drafts],
        "citation_registry": citation_registry.model_dump(),
    }

    (export_dir / EXPORT_JSON_FILENAME).write_text(json.dumps(aggregated, ensure_ascii=False, indent=2), encoding="utf-8")
    (export_dir / EXPORT_TEXT_FILENAME).write_text(final_text, encoding="utf-8")
    (export_dir / EXPORT_MD_FILENAME).write_text(final_md, encoding="utf-8")
    (export_dir / REFERENCES_JSON_FILENAME).write_text(
        json.dumps([reference.model_dump() for reference in citation_registry.references], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
