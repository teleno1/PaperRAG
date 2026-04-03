from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.core.config import get_settings
from app.domain.citation.registry import build_citation_registry, dump_citation_registry
from app.domain.models.runtime import ReviewRunResult
from app.domain.retrieval.service import RetrievalService
from app.domain.review.chapter_ops import iter_paragraphs, normalize_single_section_chapter
from app.domain.review.chapter_writer import write_chapter
from app.domain.review.final_pass_writer import write_final_pass_chapter
from app.domain.review.models import ChapterDraft, ExecutionPlan, PlannedChapter, RetrievedSource
from app.domain.review.outline_loader import dump_json, make_outline_summary
from app.domain.review.retrieval_builder import build_retrieval_artifacts
from app.domain.validation.validator import validate_pipeline_outputs
from app.infrastructure.exporters.review_exporter import (
    EXPORT_JSON_FILENAME,
    EXPORT_MD_FILENAME,
    EXPORT_TEXT_FILENAME,
    REFERENCES_JSON_FILENAME,
    export_all,
)

VALIDATION_REPORT_FILENAME = "validation_report.json"
CITATION_REGISTRY_FILENAME = "citation_registry.json"


class ReviewPipelineEngine:
    def __init__(self, retrieval_service: RetrievalService) -> None:
        self._retrieval_service = retrieval_service
        self._settings = get_settings()

    @staticmethod
    def _write_draft(draft: ChapterDraft, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(draft.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _collect_sentences(paragraphs, max_sentences: int) -> list[str]:
        collected: list[str] = []
        for paragraph in paragraphs:
            for sentence in paragraph.sentences:
                text = sentence.text.strip()
                if text:
                    collected.append(text)
                if len(collected) >= max_sentences:
                    return collected
        return collected

    def _section_digest(self, chapter: ChapterDraft, max_sentences_per_section: int) -> list[str]:
        lines: list[str] = []
        if chapter.sections:
            for section in chapter.sections[:6]:
                collected = self._collect_sentences(section.paragraphs, max_sentences_per_section)
                if collected:
                    lines.append(f"- {section.section_title}: {' '.join(collected)}")
            return lines

        collected = self._collect_sentences(iter_paragraphs(chapter), max_sentences_per_section)
        if collected:
            lines.append(f"- \u6838\u5fc3\u5185\u5bb9: {' '.join(collected)}")
        return lines

    def build_body_digest(self, body_drafts: list[ChapterDraft]) -> str:
        if not body_drafts:
            return "\u65e0\u6b63\u6587\u5185\u5bb9\u3002"
        lines: list[str] = ["\u4ee5\u4e0b\u4e3a\u6b63\u6587\u5404\u7ae0\u8282\u7684\u8f7b\u91cf\u6458\u8981\uff0c\u8bf7\u636e\u6b64\u751f\u6210\u7efc\u5408\u6027\u7ae0\u8282\uff1a"]
        for draft in body_drafts:
            lines.append(f"\n## {draft.chapter_title}")
            lines.extend(self._section_digest(draft, max_sentences_per_section=3))
        merged = "\n".join(lines).strip()
        return merged[:3500] if len(merged) > 3500 else merged

    def _write_body_chapters(
        self,
        outline_summary: str,
        chapter_bundles,
        draft_dir: Path,
    ) -> list[ChapterDraft]:
        tasks = [(outline_summary, bundle) for bundle in chapter_bundles]
        results_by_id: dict[str, ChapterDraft] = {}
        max_workers = max(1, min(self._settings.pipeline.max_workers, len(tasks)))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_bundle = {
                executor.submit(
                    write_chapter,
                    outline_summary=outline_summary,
                    bundle=bundle,
                ): bundle
                for outline_summary, bundle in tasks
            }
            for future in as_completed(future_to_bundle):
                bundle = future_to_bundle[future]
                draft = normalize_single_section_chapter(future.result())
                results_by_id[bundle.chapter_id] = draft
                self._write_draft(draft, draft_dir / f"{bundle.chapter_id}.draft.json")

        return [results_by_id[bundle.chapter_id] for bundle in chapter_bundles]

    def _final_pass_top_k(self) -> int:
        return max(3, min(8, math.ceil(self._settings.pipeline.top_k_recall * 0.7)))

    def _retrieve_final_pass_sources(
        self,
        final_chapter: PlannedChapter,
        retrieval_dir: Path,
    ) -> list[RetrievedSource]:
        query = final_chapter.query.strip()
        if not query:
            return []

        top_k = self._final_pass_top_k()
        sources = self._retrieval_service.search(query=query, top_k=top_k)
        payload = {
            "chapter_id": final_chapter.chapter_id,
            "chapter_title": final_chapter.chapter_title,
            "query": query,
            "top_k": top_k,
            "sources": [source.model_dump() for source in sources],
        }
        (retrieval_dir / f"{final_chapter.chapter_id}.sources.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return sources

    def run(self, plan: ExecutionPlan, run_dir: Path) -> ReviewRunResult:
        run_dir.mkdir(parents=True, exist_ok=True)

        dump_json(plan.model_dump(), run_dir / "00_outline" / "execution_plan.json")
        outline_summary = make_outline_summary(plan)

        chapter_bundles, source_registry, _ = build_retrieval_artifacts(
            plan=plan,
            output_dir=run_dir,
            retrieval_service=self._retrieval_service,
        )

        draft_dir = run_dir / "04_chapter_drafts"
        body_drafts = self._write_body_chapters(outline_summary, chapter_bundles, draft_dir)

        citation_registry = build_citation_registry(body_drafts, source_registry)
        dump_citation_registry(citation_registry, run_dir / "06_validation" / CITATION_REGISTRY_FILENAME)

        body_digest = self.build_body_digest(body_drafts)
        dump_json({"body_digest": body_digest}, run_dir / "05_final_pass" / "body_digest.json")

        retrieval_dir = run_dir / "02_retrieval"
        final_dir = run_dir / "05_final_pass"
        final_drafts: list[ChapterDraft] = []
        for final_chapter in plan.final_pass_chapters:
            supporting_sources = self._retrieve_final_pass_sources(final_chapter, retrieval_dir)
            draft = write_final_pass_chapter(
                outline_summary=outline_summary,
                target_chapter=final_chapter,
                body_digest=body_digest,
                supporting_sources=supporting_sources,
            )
            final_drafts.append(draft)
            self._write_draft(draft, final_dir / f"{final_chapter.chapter_id}.draft.json")

        report = validate_pipeline_outputs(
            plan=plan,
            body_drafts=body_drafts,
            final_drafts=final_drafts,
            source_registry=source_registry,
            citation_registry=citation_registry,
        )
        dump_json(report, run_dir / "06_validation" / VALIDATION_REPORT_FILENAME)

        export_all(
            plan=plan,
            body_drafts=body_drafts,
            final_drafts=final_drafts,
            citation_registry=citation_registry,
            source_registry=source_registry,
            output_dir=run_dir,
        )

        return ReviewRunResult(
            run_id=run_dir.name,
            run_dir=run_dir,
            outline_path=run_dir / "00_outline" / "outline.json",
            final_review_md=run_dir / "07_export" / EXPORT_MD_FILENAME,
            final_review_txt=run_dir / "07_export" / EXPORT_TEXT_FILENAME,
            final_review_json=run_dir / "07_export" / EXPORT_JSON_FILENAME,
            references_json=run_dir / "07_export" / REFERENCES_JSON_FILENAME,
            validation_report=run_dir / "06_validation" / VALIDATION_REPORT_FILENAME,
        )
