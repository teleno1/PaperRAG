from __future__ import annotations

from app.core.config import get_settings
from app.domain.review.chapter_ops import is_abstract_title, is_summary_outlook_title
from app.domain.review.models import (
    ChapterDraft,
    CitationRegistry,
    ExecutionPlan,
    SourceRegistry,
    ValidationIssue,
    ValidationReport,
)


def _is_fact_like(text: str) -> bool:
    markers = [
        "表明",
        "说明",
        "证明",
        "显示",
        "提出",
        "采用",
        "使用",
        "优于",
        "提升",
        "存在",
        "indicate",
        "show",
        "demonstrate",
        "propose",
        "use",
        "improve",
        "outperform",
        "suggest",
    ]
    return any(marker in text for marker in markers)


def _paragraph_groups(draft: ChapterDraft) -> list[tuple[str, list]]:
    groups: list[tuple[str, list]] = []
    if draft.paragraphs:
        groups.append((draft.chapter_id, draft.paragraphs))
    for section in draft.sections:
        groups.append((f"{draft.chapter_id}/{section.section_id}", section.paragraphs))
    return groups


def _validate_final_pass_shape(draft: ChapterDraft, issues: list[ValidationIssue]) -> None:
    if is_abstract_title(draft.chapter_title):
        if draft.sections:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="ABSTRACT_HAS_SECTIONS",
                    message="Abstract must not contain subsections.",
                    location=draft.chapter_id,
                )
            )
        if len(draft.paragraphs) != 1:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="ABSTRACT_PARAGRAPH_COUNT",
                    message="Abstract must contain exactly one paragraph.",
                    location=draft.chapter_id,
                )
            )
        if len(draft.keywords) != 5:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="ABSTRACT_KEYWORD_COUNT",
                    message="Abstract must contain exactly five keywords.",
                    location=draft.chapter_id,
                )
            )

    if is_summary_outlook_title(draft.chapter_title):
        if draft.sections:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="SUMMARY_OUTLOOK_HAS_SECTIONS",
                    message="Summary and outlook must not contain subsections.",
                    location=draft.chapter_id,
                )
            )
        if len(draft.paragraphs) != 2:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="SUMMARY_OUTLOOK_PARAGRAPH_COUNT",
                    message="Summary and outlook must contain exactly two paragraphs.",
                    location=draft.chapter_id,
                )
            )


def validate_pipeline_outputs(
    plan: ExecutionPlan,
    body_drafts: list[ChapterDraft],
    final_drafts: list[ChapterDraft],
    source_registry: SourceRegistry,
    citation_registry: CitationRegistry,
) -> ValidationReport:
    max_cites_per_sentence = get_settings().pipeline.max_cites_per_sentence
    issues: list[ValidationIssue] = []
    stats: dict[str, dict] = {}

    body_chapter_ids = {chapter.chapter_id for chapter in plan.body_chapters}
    final_chapter_ids = {chapter.chapter_id for chapter in plan.final_pass_chapters}

    for draft in body_drafts + final_drafts:
        chapter_stats = {"sentences": 0, "cited_sentences": 0, "unique_papers": 0}
        cited_papers: set[str] = set()

        if draft.chapter_id in final_chapter_ids:
            _validate_final_pass_shape(draft, issues)

        for group_location, paragraphs in _paragraph_groups(draft):
            group_sentence_count = 0
            group_cited_sentence_count = 0

            for paragraph in paragraphs:
                for sentence in paragraph.sentences:
                    chapter_stats["sentences"] += 1
                    group_sentence_count += 1
                    sentence_location = f"{group_location}/{sentence.sentence_id}"

                    if len(sentence.cite_source_ids) > max_cites_per_sentence:
                        issues.append(
                            ValidationIssue(
                                level="warning",
                                code="TOO_MANY_CITES",
                                message=f"Sentence has more than {max_cites_per_sentence} citations.",
                                location=sentence_location,
                            )
                        )

                    unknown_sources = [source_id for source_id in sentence.cite_source_ids if source_id not in source_registry.source_id_to_paper_id]
                    if unknown_sources:
                        issues.append(
                            ValidationIssue(
                                level="error",
                                code="UNKNOWN_SOURCE_ID",
                                message=f"Unknown source ids: {unknown_sources}",
                                location=sentence_location,
                            )
                        )

                    if sentence.cite_source_ids:
                        chapter_stats["cited_sentences"] += 1
                        group_cited_sentence_count += 1
                        for source_id in sentence.cite_source_ids:
                            paper_id = source_registry.source_id_to_paper_id.get(source_id)
                            if paper_id:
                                cited_papers.add(paper_id)
                    elif draft.chapter_id in body_chapter_ids and _is_fact_like(sentence.text):
                        issues.append(
                            ValidationIssue(
                                level="warning",
                                code="FACT_WITHOUT_CITATION",
                                message="Fact-like sentence without citation.",
                                location=sentence_location,
                            )
                        )

                    if draft.chapter_id in final_chapter_ids and sentence.cite_source_ids:
                        issues.append(
                            ValidationIssue(
                                level="error",
                                code="FINAL_PASS_HAS_CITATION",
                                message="Final-pass chapter should not include citations.",
                                location=sentence_location,
                            )
                        )

            if draft.chapter_id in body_chapter_ids and group_sentence_count > 0 and group_cited_sentence_count == 0:
                issues.append(
                    ValidationIssue(
                        level="warning",
                        code="SECTION_WITHOUT_ANY_CITATION",
                        message="Body section does not contain any cited sentence.",
                        location=group_location,
                    )
                )

        chapter_stats["unique_papers"] = len(cited_papers)
        stats[draft.chapter_id] = chapter_stats

    seen_ref_nos: dict[int, str] = {}
    for paper_id, ref_no in citation_registry.paper_id_to_ref_no.items():
        if ref_no in seen_ref_nos and seen_ref_nos[ref_no] != paper_id:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="DUPLICATED_REF_NO",
                    message=f"Reference number {ref_no} is assigned to multiple papers.",
                    location=paper_id,
                )
            )
        seen_ref_nos[ref_no] = paper_id

    ok = not any(issue.level == "error" for issue in issues)
    return ValidationReport(ok=ok, issues=issues, stats=stats)
