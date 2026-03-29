from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ProjectState:
    pdf_count: int
    processed_count: int
    index_ready: bool
    vector_count: int
    outlines_count: int
    latest_run_dir: str | None


@dataclass(slots=True)
class HealthStatus:
    ok: bool
    missing_keys: list[str] = field(default_factory=list)
    state: ProjectState | None = None


@dataclass(slots=True)
class PrepareCorpusResult:
    papers_dir: Path
    processed_dir: Path
    total_papers: int
    successful: int
    failed: int
    results: dict[str, bool] = field(default_factory=dict)


@dataclass(slots=True)
class BuildIndexResult:
    database_dir: Path
    index_path: Path
    metadata_path: Path
    total_vectors: int


@dataclass(slots=True)
class ReviewRunResult:
    run_id: str
    run_dir: Path
    outline_path: Path
    final_review_md: Path
    final_review_txt: Path
    final_review_json: Path
    references_json: Path
    validation_report: Path

