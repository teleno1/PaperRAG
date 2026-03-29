from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from app.core.config import get_settings
from app.domain.retrieval.service import RetrievalService
from app.domain.review.models import ChapterBundle, ExecutionPlan, RetrievedSource, SectionBundle, SectionSourceFile, SourceRegistry

SOURCE_ID_TEMPLATE = "SRC-{chapter_id}-{index:03d}"


def _safe_list_authors(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[;,，、]", value)
        return [part.strip() for part in parts if part.strip()]
    return [str(value)]


def _normalize_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff_]+", "", text)
    return text or "unknown"


def _make_paper_id(item: dict) -> str:
    if item.get("paper_id"):
        return str(item["paper_id"])
    title = _normalize_text(str(item.get("title", "")))
    year = _normalize_text(str(item.get("year", "")))
    venue = _normalize_text(str(item.get("venue", "")))
    return f"{title}__{year}__{venue}"[:180]


def _make_chunk_id(item: dict, paper_id: str) -> str:
    if item.get("chunk_id"):
        return str(item["chunk_id"])
    raw = f"{paper_id}|{item.get('section', '')}|{item.get('content', '')}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{paper_id}__{digest}"


def _normalize_result_item(item: dict) -> dict:
    paper_id = _make_paper_id(item)
    return {
        "paper_id": paper_id,
        "chunk_id": _make_chunk_id(item, paper_id),
        "title": str(item.get("title", "") or ""),
        "authors": _safe_list_authors(item.get("authors")),
        "year": str(item.get("year", "") or ""),
        "venue": str(item.get("venue", "") or ""),
        "section": str(item.get("section", "") or ""),
        "content": str(item.get("content", "") or ""),
        "paper_score": item.get("paper_score"),
        "chunk_score": item.get("chunk_score"),
    }


def _top_k_for_policy(citation_policy: str, base_top_k: int) -> int:
    if citation_policy == "required":
        return base_top_k
    if citation_policy == "optional":
        return max(1, math.ceil(base_top_k * 0.7))
    return max(1, math.ceil(base_top_k * 0.4))


def build_retrieval_artifacts(
    plan: ExecutionPlan,
    output_dir: str | Path,
    retrieval_service: RetrievalService,
) -> tuple[list[ChapterBundle], SourceRegistry, list[SectionSourceFile]]:
    root = Path(output_dir)
    retrieval_dir = root / "02_retrieval"
    bundle_dir = root / "03_chapter_bundles"
    retrieval_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    source_registry = SourceRegistry()
    chapter_bundles: list[ChapterBundle] = []
    section_files: list[SectionSourceFile] = []
    base_top_k = max(get_settings().pipeline.top_k_recall, 1)

    for chapter in plan.body_chapters:
        chunk_key_to_source_id: dict[str, str] = {}
        unique_sources: list[RetrievedSource] = []
        leaf_section_bundles: list[SectionBundle] = []
        source_counter = 0

        for leaf in chapter.leaf_sections:
            raw_results = [
                item.model_dump()
                for item in retrieval_service.search(
                    leaf.query,
                    top_k=_top_k_for_policy(leaf.citation_policy, base_top_k),
                )
            ]
            section_source_ids: list[str] = []
            section_sources: list[RetrievedSource] = []

            for item in raw_results:
                normalized = _normalize_result_item(item)
                chunk_key = normalized["chunk_id"]

                if chunk_key in chunk_key_to_source_id:
                    source_id = chunk_key_to_source_id[chunk_key]
                    existing = next(source for source in unique_sources if source.source_id == source_id)
                    section_source_ids.append(source_id)
                    section_sources.append(existing)
                    continue

                source_counter += 1
                source_id = SOURCE_ID_TEMPLATE.format(chapter_id=chapter.chapter_id, index=source_counter)
                chunk_key_to_source_id[chunk_key] = source_id

                source = RetrievedSource(
                    source_id=source_id,
                    paper_id=normalized["paper_id"],
                    chunk_id=normalized["chunk_id"],
                    title=normalized["title"],
                    authors=normalized["authors"],
                    year=normalized["year"],
                    venue=normalized["venue"],
                    section=normalized["section"],
                    content=normalized["content"],
                    paper_score=normalized["paper_score"],
                    chunk_score=normalized["chunk_score"],
                )
                unique_sources.append(source)
                section_source_ids.append(source_id)
                section_sources.append(source)

                source_registry.source_id_to_chunk_id[source_id] = source.chunk_id
                source_registry.source_id_to_paper_id[source_id] = source.paper_id
                if source.paper_id not in source_registry.paper_id_to_metadata:
                    source_registry.paper_id_to_metadata[source.paper_id] = {
                        "title": source.title,
                        "authors": source.authors,
                        "year": source.year,
                        "venue": source.venue,
                    }

            leaf_section_bundles.append(
                SectionBundle(
                    section_id=leaf.section_id,
                    section_title=leaf.title,
                    section_description=leaf.description,
                    section_query=leaf.query,
                    citation_policy=leaf.citation_policy,
                    source_ids=section_source_ids,
                )
            )

            section_file = SectionSourceFile(
                chapter_id=chapter.chapter_id,
                chapter_title=chapter.chapter_title,
                section_id=leaf.section_id,
                section_title=leaf.title,
                section_description=leaf.description,
                section_query=leaf.query,
                citation_policy=leaf.citation_policy,
                source_ids=section_source_ids,
                sources=section_sources,
            )
            section_files.append(section_file)
            (retrieval_dir / f"{leaf.section_id}.sources.json").write_text(
                json.dumps(section_file.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        chapter_bundle = ChapterBundle(
            chapter_id=chapter.chapter_id,
            chapter_title=chapter.chapter_title,
            chapter_description=chapter.chapter_description,
            chapter_query=chapter.query,
            chapter_citation_policy=chapter.citation_policy,
            leaf_sections=leaf_section_bundles,
            unique_sources=unique_sources,
            all_source_ids=[source.source_id for source in unique_sources],
        )
        chapter_bundles.append(chapter_bundle)
        (bundle_dir / f"{chapter.chapter_id}.bundle.json").write_text(
            json.dumps(chapter_bundle.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    (retrieval_dir / "source_registry.json").write_text(
        json.dumps(source_registry.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return chapter_bundles, source_registry, section_files
