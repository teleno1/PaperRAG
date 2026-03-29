import json
from pathlib import Path

from app.domain.models.runtime import ReviewRunResult
from app.domain.review.engine import ReviewPipelineEngine
from app.domain.review.models import (
    ChapterDraft,
    ExecutionPlan,
    ParagraphDraft,
    PlannedChapter,
    RetrievedSource,
    SectionDraft,
    SentenceDraft,
)


class FakeRetrievalService:
    def search(self, query: str, top_k: int = 20):
        return [
            RetrievedSource(
                source_id="chunk-1",
                paper_id="paper-1",
                chunk_id="chunk-1",
                title="Paper",
                authors=["Author"],
                year="2024",
                venue="Venue",
                section="Intro",
                content=f"Evidence for {query}",
                paper_score=1.0,
                chunk_score=1.0,
            )
        ]


def _draft(chapter_id: str, chapter_title: str, cite: bool = True) -> ChapterDraft:
    sentence = SentenceDraft(
        sentence_id="S1",
        text="Body sentence.",
        cite_source_ids=["SRC-CH01-001"] if cite else [],
    )
    return ChapterDraft(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        sections=[
            SectionDraft(
                section_id=f"{chapter_id}-SEC01",
                section_title="Section 1",
                paragraphs=[ParagraphDraft(paragraph_id="P1", sentences=[sentence])],
            )
        ],
    )


def test_engine_writes_single_layer_run_dir(tmp_path, monkeypatch):
    import app.domain.review.engine as engine_module

    monkeypatch.setattr(engine_module, "write_chapter", lambda **kwargs: _draft(kwargs["bundle"].chapter_id, kwargs["bundle"].chapter_title))
    monkeypatch.setattr(
        engine_module,
        "write_final_pass_chapter",
        lambda **kwargs: _draft(kwargs["target_chapter"].chapter_id, kwargs["target_chapter"].chapter_title, cite=False),
    )

    plan = ExecutionPlan(
        title="Demo",
        body_chapters=[
            PlannedChapter(
                chapter_id="CH01",
                chapter_title="Background",
                chapter_description="desc",
                query="background",
                leaf_sections=[],
            )
        ],
        final_pass_chapters=[
            PlannedChapter(
                chapter_id="FP01",
                chapter_title="Conclusion",
                chapter_description="desc",
                query="",
                write_stage="final_pass",
                citation_policy="none",
                leaf_sections=[],
            )
        ],
    )
    plan.body_chapters[0].leaf_sections = [
        {
            "chapter_id": "CH01",
            "chapter_title": "Background",
            "section_id": "CH01-SEC01",
            "title": "Background section",
            "description": "desc",
            "query": "background",
            "citation_policy": "required",
            "write_stage": "body",
        }
    ]
    plan = ExecutionPlan.model_validate(plan.model_dump())

    run_dir = tmp_path / "20260326_151530_abc123"
    result = ReviewPipelineEngine(FakeRetrievalService()).run(plan=plan, run_dir=run_dir)

    assert result.run_dir == run_dir
    assert not (run_dir / run_dir.name).exists()
    for stage in [
        "00_outline",
        "02_retrieval",
        "03_chapter_bundles",
        "04_chapter_drafts",
        "05_final_pass",
        "06_validation",
        "07_export",
    ]:
        assert (run_dir / stage).exists()

