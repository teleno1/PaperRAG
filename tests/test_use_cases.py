import json
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.core.exceptions import InsufficientPapersError
from app.core.paths import PathManager
from app.domain.models.runtime import BuildIndexResult, ReviewRunResult
from app.use_cases.build_index import BuildIndexUseCase
from app.use_cases.generate_outline import GenerateOutlineUseCase
from app.use_cases.prepare_corpus import PrepareCorpusUseCase
from app.use_cases.run_review_from_outline import RunReviewFromOutlineUseCase
from app.use_cases.run_review_from_topic import RunReviewFromTopicUseCase


def _paths(tmp_path) -> PathManager:
    settings = get_settings().model_copy(deep=True)
    settings.paths.papers_dir = str(tmp_path / "papers")
    settings.paths.processed_dir = str(tmp_path / "processed")
    settings.paths.database_dir = str(tmp_path / "database")
    settings.paths.outlines_dir = str(tmp_path / "outlines")
    settings.paths.outputs_dir = str(tmp_path / "review_outputs")
    settings.pipeline.min_papers_for_review = 1
    return PathManager(settings_override=settings)


class FakeMinerUClient:
    def parse_pdf(self, pdf_path: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "content_list_v2.json").write_text("[]", encoding="utf-8")
        return output_dir


class FakeIndexBuilder:
    def build(self, processed_dir: Path):
        return [[0.1, 0.2]], [{"paper_id": "paper-1", "chunk_id": "chunk-1", "content": "text"}]


class FakePlanner:
    def plan(self, topic: str) -> dict:
        return {"title": topic, "language": "中文", "sections": []}


class FakeEngine:
    def run(self, plan, run_dir: Path):
        return ReviewRunResult(
            run_id=run_dir.name,
            run_dir=run_dir,
            outline_path=run_dir / "00_outline" / "outline.json",
            final_review_md=run_dir / "07_export" / "final_review.md",
            final_review_txt=run_dir / "07_export" / "final_review.txt",
            final_review_json=run_dir / "07_export" / "final_review.json",
            references_json=run_dir / "07_export" / "references.json",
            validation_report=run_dir / "06_validation" / "validation_report.json",
        )


class FakeBuildIndexUseCase:
    def execute(self, force: bool = False):
        return BuildIndexResult(
            database_dir=Path("/tmp/db"),
            index_path=Path("/tmp/db/paper_index.faiss"),
            metadata_path=Path("/tmp/db/metadata.json"),
            total_vectors=1,
        )


class FakeGenerateOutlineUseCase:
    def execute(self, topic: str):
        return Path("/tmp/outline.json")


class FakeRunReviewFromOutlineUseCase:
    def execute(self, outline_path: Path):
        return ReviewRunResult(
            run_id="run-1",
            run_dir=Path("/tmp/run-1"),
            outline_path=outline_path,
            final_review_md=Path("/tmp/run-1/07_export/final_review.md"),
            final_review_txt=Path("/tmp/run-1/07_export/final_review.txt"),
            final_review_json=Path("/tmp/run-1/07_export/final_review.json"),
            references_json=Path("/tmp/run-1/07_export/references.json"),
            validation_report=Path("/tmp/run-1/06_validation/validation_report.json"),
        )


def test_prepare_corpus_use_case(tmp_path):
    paths = _paths(tmp_path)
    paths.ensure_dirs()
    (paths.papers_dir / "paper1.pdf").write_bytes(b"%PDF")
    result = PrepareCorpusUseCase(mineru_client=FakeMinerUClient(), paths=paths).execute(force=False)
    assert result.total_papers == 1
    assert result.successful == 1


def test_build_index_use_case(tmp_path):
    paths = _paths(tmp_path)
    paths.ensure_dirs()
    processed = paths.processed_dir / "paper1"
    processed.mkdir(parents=True)
    (processed / "content_list_v2.json").write_text("[]", encoding="utf-8")
    result = BuildIndexUseCase(index_builder=FakeIndexBuilder(), paths=paths).execute(force=True)
    assert result.total_vectors == 1
    assert result.index_path.exists()


def test_generate_outline_use_case(tmp_path):
    paths = _paths(tmp_path)
    (paths.papers_dir / "paper1.pdf").parent.mkdir(parents=True, exist_ok=True)
    (paths.papers_dir / "paper1.pdf").write_bytes(b"%PDF")
    result = GenerateOutlineUseCase(
        planner=FakePlanner(),
        build_index_use_case=FakeBuildIndexUseCase(),
        paths=paths,
    ).execute("Test Topic")
    assert result.exists()
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["title"] == "Test Topic"


def test_generate_outline_use_case_checks_minimum_papers(tmp_path):
    settings = get_settings().model_copy(deep=True)
    settings.paths.papers_dir = str(tmp_path / "papers")
    settings.paths.processed_dir = str(tmp_path / "processed")
    settings.paths.database_dir = str(tmp_path / "database")
    settings.paths.outlines_dir = str(tmp_path / "outlines")
    settings.paths.outputs_dir = str(tmp_path / "review_outputs")
    settings.pipeline.min_papers_for_review = 2
    paths = PathManager(settings_override=settings)
    paths.ensure_dirs()
    (paths.papers_dir / "paper1.pdf").write_bytes(b"%PDF")

    with pytest.raises(InsufficientPapersError):
        GenerateOutlineUseCase(
            planner=FakePlanner(),
            build_index_use_case=FakeBuildIndexUseCase(),
            paths=paths,
        ).execute("Test Topic")


def test_run_review_from_outline_use_case(tmp_path):
    paths = _paths(tmp_path)
    (paths.papers_dir / "paper1.pdf").parent.mkdir(parents=True, exist_ok=True)
    (paths.papers_dir / "paper1.pdf").write_bytes(b"%PDF")
    outline_dir = paths.outlines_dir / "demo"
    outline_dir.mkdir(parents=True, exist_ok=True)
    outline_path = outline_dir / "outline.json"
    outline_path.write_text(json.dumps({"title": "Demo", "sections": []}, ensure_ascii=False), encoding="utf-8")
    result = RunReviewFromOutlineUseCase(engine=FakeEngine(), paths=paths).execute(outline_path=outline_path, run_id="run-123")
    assert result.run_dir == paths.outputs_dir / "run-123"
    assert (result.run_dir / "00_outline" / "outline.json").exists()


def test_run_review_from_topic_use_case():
    result = RunReviewFromTopicUseCase(
        build_index_use_case=FakeBuildIndexUseCase(),
        generate_outline_use_case=FakeGenerateOutlineUseCase(),
        run_review_from_outline_use_case=FakeRunReviewFromOutlineUseCase(),
    ).execute("Topic", ensure_index=True)
    assert result.run_id == "run-1"
