from textwrap import dedent

from app.core import config
from app.domain.review.models import ExecutionPlan
from app.domain.review.retrieval_builder import build_retrieval_artifacts


def _write_settings(path, body: str) -> None:
    path.write_text(dedent(body).strip() + "\n", encoding="utf-8")


class FakeRetrievedSource:
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self.paper_id = f"paper-{source_id}"
        self.chunk_id = f"chunk-{source_id}"
        self.title = f"title-{source_id}"
        self.authors = ["author"]
        self.year = "2024"
        self.venue = "venue"
        self.section = "intro"
        self.content = "content"
        self.paper_score = 1.0
        self.chunk_score = 1.0

    def model_dump(self) -> dict:
        return {
            "source_id": self.source_id,
            "paper_id": self.paper_id,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "section": self.section,
            "content": self.content,
            "paper_score": self.paper_score,
            "chunk_score": self.chunk_score,
        }


class FakeRetrievalService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, top_k: int = 20):
        self.calls.append((query, top_k))
        return [FakeRetrievedSource("1")]


def test_retrieval_builder_uses_configured_top_k_recall(monkeypatch, tmp_path):
    config_path = tmp_path / "settings.yaml"
    _write_settings(
        config_path,
        """
        pipeline:
          top_k_recall: 11
        """,
    )
    monkeypatch.setenv("PAPERRAG_CONFIG_PATH", str(config_path))
    config._settings = None

    plan = ExecutionPlan.model_validate(
        {
            "title": "Demo",
            "language": "English",
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
            "final_pass_chapters": [],
        }
    )

    retrieval_service = FakeRetrievalService()
    build_retrieval_artifacts(plan=plan, output_dir=tmp_path / "run", retrieval_service=retrieval_service)

    assert retrieval_service.calls == [("background", 11)]
