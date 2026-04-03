from __future__ import annotations

import json
from pathlib import Path

from app.domain.review.chapter_ops import iter_sentences
from app.domain.review.models import ChapterDraft, CitationRegistry, ReferenceEntry, SourceRegistry


def build_citation_registry(
    body_chapter_drafts: list[ChapterDraft],
    source_registry: SourceRegistry,
) -> CitationRegistry:
    paper_id_to_ref_no: dict[str, int] = {}
    next_ref = 1

    for chapter in body_chapter_drafts:
        for sentence in iter_sentences(chapter):
            seen_papers_in_sentence: set[str] = set()
            for source_id in sentence.cite_source_ids:
                paper_id = source_registry.source_id_to_paper_id.get(source_id)
                if not paper_id or paper_id in seen_papers_in_sentence:
                    continue
                seen_papers_in_sentence.add(paper_id)
                if paper_id not in paper_id_to_ref_no:
                    paper_id_to_ref_no[paper_id] = next_ref
                    next_ref += 1

    references = []
    for paper_id, ref_no in sorted(paper_id_to_ref_no.items(), key=lambda item: item[1]):
        meta = source_registry.paper_id_to_metadata.get(paper_id, {})
        references.append(
            ReferenceEntry(
                ref_no=ref_no,
                paper_id=paper_id,
                title=str(meta.get("title", "") or ""),
                authors=list(meta.get("authors", []) or []),
                year=str(meta.get("year", "") or ""),
                venue=str(meta.get("venue", "") or ""),
            )
        )

    return CitationRegistry(
        paper_id_to_ref_no=paper_id_to_ref_no,
        source_id_to_paper_id=source_registry.source_id_to_paper_id,
        paper_id_to_metadata=source_registry.paper_id_to_metadata,
        references=references,
    )


def dump_citation_registry(registry: CitationRegistry, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(registry.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
