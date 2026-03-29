from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.core.config import get_settings
from app.domain.citation.registry import build_citation_registry, dump_citation_registry
from app.domain.models.runtime import ReviewRunResult
from app.domain.retrieval.service import RetrievalService
from app.domain.review.chapter_writer import write_chapter
from app.domain.review.final_pass_writer import write_final_pass_chapter
from app.domain.review.models import ChapterDraft, ExecutionPlan
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
    def _chapter_plain_without_refs(chapter: ChapterDraft) -> str:
        lines = [chapter.chapter_title]
        for section in chapter.sections:
            lines.append(section.section_title)
            for paragraph in section.paragraphs:
                paragraph_text = "".join(sentence.text.strip() for sentence in paragraph.sentences)
                if paragraph_text.strip():
                    lines.append(paragraph_text.strip())
        return "\n".join(lines)

    def _build_previous_recap(self, body_drafts: list[ChapterDraft]) -> str:
        if not body_drafts:
            return "无"
        texts = [self._chapter_plain_without_refs(draft) for draft in body_drafts[-2:]]
        merged = "\n\n".join(texts)
        max_chars = self._settings.pipeline.previous_recap_chars
        return merged[-max_chars:] if len(merged) > max_chars else merged

    def _section_digest(self, chapter: ChapterDraft, max_sentences_per_section: int) -> list[str]:
        lines: list[str] = []
        for section in chapter.sections[:6]:
            collected: list[str] = []
            for paragraph in section.paragraphs:
                for sentence in paragraph.sentences:
                    text = sentence.text.strip()
                    if text:
                        collected.append(text)
                    if len(collected) >= max_sentences_per_section:
                        break
                if len(collected) >= max_sentences_per_section:
                    break
            if collected:
                lines.append(f"- {section.section_title}: {' '.join(collected)}")
        return lines

    def build_body_digest(self, body_drafts: list[ChapterDraft]) -> str:
        if not body_drafts:
            return "无"
        lines: list[str] = ["以下为正文各章节的轻量摘要，请据此生成综合性章节："]
        for draft in body_drafts:
            lines.append(f"\n## {draft.chapter_title}")
            lines.extend(self._section_digest(draft, max_sentences_per_section=3))
        merged = "\n".join(lines).strip()
        return merged[:3500] if len(merged) > 3500 else merged

    def _write_body_chapters_parallel(
        self,
        outline_summary: str,
        chapter_bundles,
        draft_dir: Path,
    ) -> list[ChapterDraft]:
        placeholder_recap = "无（正文章节采用并行生成，未提供前文章节回顾）"
        citation_snapshot: dict = {}
        tasks = [
            (outline_summary, bundle, placeholder_recap, citation_snapshot)
            for bundle in chapter_bundles
        ]
        results_by_id: dict[str, ChapterDraft] = {}
        max_workers = max(1, min(self._settings.pipeline.max_workers, len(tasks)))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_bundle = {
                executor.submit(
                    write_chapter,
                    outline_summary=outline_summary,
                    bundle=bundle,
                    previous_recap=previous_recap,
                    citation_snapshot=snapshot,
                ): bundle
                for outline_summary, bundle, previous_recap, snapshot in tasks
            }
            for future in as_completed(future_to_bundle):
                bundle = future_to_bundle[future]
                draft = future.result()
                results_by_id[bundle.chapter_id] = draft
                self._write_draft(draft, draft_dir / f"{bundle.chapter_id}.draft.json")

        return [results_by_id[bundle.chapter_id] for bundle in chapter_bundles]

    def _write_body_chapters_serial(
        self,
        outline_summary: str,
        chapter_bundles,
        draft_dir: Path,
    ) -> list[ChapterDraft]:
        body_drafts: list[ChapterDraft] = []
        citation_snapshot: dict = {}
        for bundle in chapter_bundles:
            previous_recap = self._build_previous_recap(body_drafts)
            draft = write_chapter(
                outline_summary=outline_summary,
                bundle=bundle,
                previous_recap=previous_recap,
                citation_snapshot=citation_snapshot,
            )
            body_drafts.append(draft)
            self._write_draft(draft, draft_dir / f"{bundle.chapter_id}.draft.json")
        return body_drafts

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
        if self._settings.pipeline.parallel_body_writing:
            body_drafts = self._write_body_chapters_parallel(outline_summary, chapter_bundles, draft_dir)
        else:
            body_drafts = self._write_body_chapters_serial(outline_summary, chapter_bundles, draft_dir)

        citation_registry = build_citation_registry(body_drafts, source_registry)
        dump_citation_registry(citation_registry, run_dir / "06_validation" / CITATION_REGISTRY_FILENAME)

        body_digest = self.build_body_digest(body_drafts)
        dump_json({"body_digest": body_digest}, run_dir / "05_final_pass" / "body_digest.json")

        final_dir = run_dir / "05_final_pass"
        final_drafts: list[ChapterDraft] = []
        for final_chapter in plan.final_pass_chapters:
            draft = write_final_pass_chapter(
                outline_summary=outline_summary,
                target_chapter=final_chapter,
                body_digest=body_digest,
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
