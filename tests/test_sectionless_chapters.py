import json

from app.domain.citation.registry import build_citation_registry
from app.domain.review.engine import ReviewPipelineEngine
from app.domain.review.models import (
    ChapterDraft,
    ExecutionPlan,
    ParagraphDraft,
    PlannedChapter,
    RetrievedSource,
    SectionDraft,
    SentenceDraft,
    SourceRegistry,
)
from app.domain.validation.validator import validate_pipeline_outputs


class RecordingRetrievalService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def search(self, query: str, top_k: int = 20):
        self.calls.append({"query": query, "top_k": top_k})
        return [
            RetrievedSource(
                source_id="chunk-1",
                paper_id=f"paper-{query}",
                chunk_id=f"chunk-{query}",
                title=f"Paper for {query}",
                authors=["Author"],
                year="2024",
                venue="Venue",
                section="Intro",
                content=f"Evidence for {query}",
                paper_score=1.0,
                chunk_score=1.0,
            )
        ]


def _sentence(sentence_id: str, text: str, cite_source_ids: list[str] | None = None) -> SentenceDraft:
    return SentenceDraft(sentence_id=sentence_id, text=text, cite_source_ids=cite_source_ids or [])


def _paragraph(paragraph_id: str, *sentences: SentenceDraft) -> ParagraphDraft:
    return ParagraphDraft(paragraph_id=paragraph_id, sentences=list(sentences))


def test_engine_flattens_single_section_and_retrieves_outlook(tmp_path, monkeypatch):
    import app.domain.review.engine as engine_module

    retrieval = RecordingRetrievalService()
    final_pass_sources: dict[str, list[RetrievedSource]] = {}

    def fake_write_chapter(**kwargs):
        bundle = kwargs["bundle"]
        return ChapterDraft(
            chapter_id=bundle.chapter_id,
            chapter_title=bundle.chapter_title,
            sections=[
                SectionDraft(
                    section_id=f"{bundle.chapter_id}-SEC01",
                    section_title="\u552f\u4e00\u5c0f\u8282",
                    paragraphs=[
                        _paragraph(
                            "P1",
                            _sentence("S1", "\u6b63\u6587\u4e8b\u5b9e\u53e5\u3002", ["SRC-CH01-001"]),
                        )
                    ],
                )
            ],
        )

    def fake_write_final_pass_chapter(**kwargs):
        chapter = kwargs["target_chapter"]
        final_pass_sources[chapter.chapter_id] = list(kwargs.get("supporting_sources") or [])
        if chapter.chapter_title == "\u6458\u8981":
            return ChapterDraft(
                chapter_id=chapter.chapter_id,
                chapter_title=chapter.chapter_title,
                paragraphs=[_paragraph("P1", _sentence("S1", "\u8fd9\u662f\u4e00\u6bb5\u6458\u8981\u3002"))],
                keywords=[
                    "\u65f6\u5e8f\u9884\u6d4b",
                    "\u7efc\u8ff0",
                    "\u7814\u7a76\u73b0\u72b6",
                    "\u5173\u952e\u95ee\u9898",
                    "\u53d1\u5c55\u8d8b\u52bf",
                ],
            )
        return ChapterDraft(
            chapter_id=chapter.chapter_id,
            chapter_title=chapter.chapter_title,
            paragraphs=[
                _paragraph("P1", _sentence("S1", "\u8fd9\u662f\u603b\u7ed3\u6bb5\u3002")),
                _paragraph("P2", _sentence("S2", "\u8fd9\u662f\u5c55\u671b\u6bb5\u3002")),
            ],
        )

    monkeypatch.setattr(engine_module, "write_chapter", fake_write_chapter)
    monkeypatch.setattr(engine_module, "write_final_pass_chapter", fake_write_final_pass_chapter)

    plan = ExecutionPlan(
        title="Demo",
        language="\u4e2d\u6587",
        body_chapters=[
            PlannedChapter(
                chapter_id="CH01",
                chapter_title="\u7814\u7a76\u73b0\u72b6",
                chapter_description="desc",
                query="background",
                leaf_sections=[
                    {
                        "chapter_id": "CH01",
                        "chapter_title": "\u7814\u7a76\u73b0\u72b6",
                        "section_id": "CH01-SEC01",
                        "title": "\u552f\u4e00\u5c0f\u8282",
                        "description": "desc",
                        "query": "background",
                        "citation_policy": "required",
                        "write_stage": "body",
                    }
                ],
            )
        ],
        final_pass_chapters=[
            PlannedChapter(
                chapter_id="FP01",
                chapter_title="\u6458\u8981",
                chapter_description="desc",
                query="",
                write_stage="final_pass",
                citation_policy="none",
            ),
            PlannedChapter(
                chapter_id="FP02",
                chapter_title="\u603b\u7ed3\u4e0e\u5c55\u671b",
                chapter_description="desc",
                query="future trend query",
                write_stage="final_pass",
                citation_policy="none",
            ),
        ],
    )
    plan = ExecutionPlan.model_validate(plan.model_dump())

    run_dir = tmp_path / "run"
    result = ReviewPipelineEngine(retrieval).run(plan=plan, run_dir=run_dir)

    assert any(call["query"] == "background" for call in retrieval.calls)
    assert any(call["query"] == "future trend query" for call in retrieval.calls)
    assert not (run_dir / "02_retrieval" / "FP01.sources.json").exists()
    assert (run_dir / "02_retrieval" / "FP02.sources.json").exists()
    assert final_pass_sources["FP01"] == []
    assert len(final_pass_sources["FP02"]) == 1
    assert final_pass_sources["FP02"][0].content == "Evidence for future trend query"

    body_draft = json.loads((run_dir / "04_chapter_drafts" / "CH01.draft.json").read_text(encoding="utf-8"))
    assert body_draft["sections"] == []
    assert len(body_draft["paragraphs"]) == 1

    export_md = result.final_review_md.read_text(encoding="utf-8")
    assert "## \u552f\u4e00\u5c0f\u8282" not in export_md
    assert "\u5173\u952e\u8bcd\uff1a\u65f6\u5e8f\u9884\u6d4b\uff1b\u7efc\u8ff0\uff1b\u7814\u7a76\u73b0\u72b6\uff1b\u5173\u952e\u95ee\u9898\uff1b\u53d1\u5c55\u8d8b\u52bf" in export_md
    assert "# \u6458\u8981" in export_md
    assert "# \u603b\u7ed3\u4e0e\u5c55\u671b" in export_md

    final_review = json.loads(result.final_review_json.read_text(encoding="utf-8"))
    assert final_review["body_chapters"][0]["sections"] == []
    assert len(final_review["body_chapters"][0]["paragraphs"]) == 1
    final_by_id = {chapter["chapter_id"]: chapter for chapter in final_review["final_pass_chapters"]}
    assert len(final_by_id["FP01"]["keywords"]) == 5
    assert final_by_id["FP02"]["keywords"] == []


def test_validator_handles_sectionless_final_pass_shapes():
    plan = ExecutionPlan(
        title="Demo",
        body_chapters=[],
        final_pass_chapters=[
            PlannedChapter(
                chapter_id="FP01",
                chapter_title="\u6458\u8981",
                query="",
                write_stage="final_pass",
                citation_policy="none",
            ),
            PlannedChapter(
                chapter_id="FP02",
                chapter_title="\u603b\u7ed3\u4e0e\u5c55\u671b",
                query="future trend query",
                write_stage="final_pass",
                citation_policy="none",
            ),
        ],
    )

    final_drafts = [
        ChapterDraft(
            chapter_id="FP01",
            chapter_title="\u6458\u8981",
            paragraphs=[_paragraph("P1", _sentence("S1", "\u6458\u8981\u53e5\u3002", ["SRC-CH01-001"]))],
            keywords=["\u5173\u952e\u8bcd1", "\u5173\u952e\u8bcd2"],
        ),
        ChapterDraft(
            chapter_id="FP02",
            chapter_title="\u603b\u7ed3\u4e0e\u5c55\u671b",
            paragraphs=[_paragraph("P1", _sentence("S1", "\u603b\u7ed3\u53e5\u3002"))],
        ),
    ]

    source_registry = SourceRegistry(
        source_id_to_paper_id={"SRC-CH01-001": "paper-1"},
        paper_id_to_metadata={"paper-1": {"title": "Paper", "authors": ["A"], "year": "2024", "venue": "Venue"}},
    )
    citation_registry = build_citation_registry([], source_registry)

    report = validate_pipeline_outputs(
        plan=plan,
        body_drafts=[],
        final_drafts=final_drafts,
        source_registry=source_registry,
        citation_registry=citation_registry,
    )

    codes = {issue.code for issue in report.issues}
    assert "FINAL_PASS_HAS_CITATION" in codes
    assert "ABSTRACT_KEYWORD_COUNT" in codes
    assert "SUMMARY_OUTLOOK_PARAGRAPH_COUNT" in codes
    assert report.stats["FP01"]["sentences"] == 1
