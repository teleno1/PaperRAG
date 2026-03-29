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
    return ChapterDraft(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        sections=[
            SectionDraft(
                section_id=f"{chapter_id}-SEC01",
                section_title="Section",
                paragraphs=[
                    ParagraphDraft(
                        paragraph_id="P1",
                        sentences=[
                            SentenceDraft(
                                sentence_id="S1",
                                text="Sentence.",
                                cite_source_ids=["SRC-CH01-001"] if cite else [],
                            )
                        ],
                    )
                ],
            )
        ],
    )


def test_review_engine_stage_outputs(tmp_path, monkeypatch):
    import app.domain.review.engine as engine_module

    monkeypatch.setattr(engine_module, "write_chapter", lambda **kwargs: _draft(kwargs["bundle"].chapter_id, kwargs["bundle"].chapter_title))
    monkeypatch.setattr(
        engine_module,
        "write_final_pass_chapter",
        lambda **kwargs: _draft(kwargs["target_chapter"].chapter_id, kwargs["target_chapter"].chapter_title, cite=False),
    )

    plan = ExecutionPlan.model_validate(
        {
            "title": "Demo",
            "language": "中文",
            "body_chapters": [
                {
                    "chapter_id": "CH01",
                    "chapter_title": "Background",
                    "chapter_description": "desc",
                    "query": "background",
                    "citation_policy": "required",
                    "write_stage": "body",
                    "leaf_sections": [
                        {
                            "chapter_id": "CH01",
                            "chapter_title": "Background",
                            "section_id": "CH01-SEC01",
                            "title": "Background Section",
                            "description": "desc",
                            "query": "background",
                            "citation_policy": "required",
                            "write_stage": "body",
                        }
                    ],
                }
            ],
            "final_pass_chapters": [
                {
                    "chapter_id": "FP01",
                    "chapter_title": "Conclusion",
                    "chapter_description": "desc",
                    "query": "",
                    "citation_policy": "none",
                    "write_stage": "final_pass",
                    "leaf_sections": [],
                }
            ],
        }
    )

    result = engine_module.ReviewPipelineEngine(FakeRetrievalService()).run(plan=plan, run_dir=tmp_path / "run1")
    assert result.final_review_json.exists()
    assert result.references_json.exists()
    assert result.validation_report.exists()

