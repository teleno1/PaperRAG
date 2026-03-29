"""Compatibility facade for high-level pipeline orchestration."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from app.core.paths import get_paths
from app.use_cases._shared import ensure_required_keys
from app.use_cases.build_index import BuildIndexUseCase
from app.use_cases.generate_outline import GenerateOutlineUseCase
from app.use_cases.health_and_state import HealthAndStateUseCase
from app.use_cases.prepare_corpus import PrepareCorpusUseCase
from app.use_cases.run_review_from_outline import RunReviewFromOutlineUseCase


class PipelineService:
    """Thin compatibility wrapper around the new use-case layer."""

    def __init__(
        self,
        parser_service=None,
        index_service=None,
        outline_service=None,
        review_service=None,
    ):
        self._paths = get_paths()
        self._prepare_corpus = PrepareCorpusUseCase(paths=self._paths)
        self._build_index = BuildIndexUseCase(
            prepare_corpus_use_case=self._prepare_corpus,
            paths=self._paths,
        )
        self._generate_outline = GenerateOutlineUseCase(
            build_index_use_case=self._build_index,
            paths=self._paths,
        )
        self._run_review = RunReviewFromOutlineUseCase(paths=self._paths)
        self._health_and_state = HealthAndStateUseCase(paths=self._paths)

    def run(
        self,
        topic: str,
        force_reparse: bool = False,
        force_rebuild_index: bool = False,
        run_id: Optional[str] = None,
    ) -> dict:
        start_time = time.time()
        ensure_required_keys()

        if force_reparse:
            self._prepare_corpus.execute(force=True)
        index_result = self._build_index.execute(force=force_rebuild_index or force_reparse)
        outline_path = self._generate_outline.execute(topic)
        review_result = self._run_review.execute(outline_path=outline_path, run_id=run_id)

        return {
            "topic": topic,
            "outline_path": str(outline_path),
            "run_dir": str(review_result.run_dir),
            "final_review_md": str(review_result.final_review_md),
            "final_review_txt": str(review_result.final_review_txt),
            "final_review_json": str(review_result.final_review_json),
            "references_json": str(review_result.references_json),
            "validation_report": str(review_result.validation_report),
            "vector_count": index_result.total_vectors,
            "elapsed_time": time.time() - start_time,
        }

    def check_state(self) -> dict:
        state = self._health_and_state.get_state()
        return {
            "papers_dir": str(self._paths.papers_dir),
            "papers_count": state.pdf_count,
            "processed_dir": str(self._paths.processed_dir),
            "processed_count": state.processed_count,
            "database_dir": str(self._paths.database_dir),
            "database_ready": state.index_ready,
            "index_path": str(self._paths.faiss_index_path) if state.index_ready else None,
            "metadata_path": str(self._paths.metadata_path) if state.index_ready else None,
            "vector_count": state.vector_count,
            "outlines_count": state.outlines_count,
            "latest_run_dir": state.latest_run_dir,
        }

    def health_check(self) -> dict:
        health = self._health_and_state.get_health()
        state = health.state
        return {
            "status": "ok" if health.ok else "error",
            "database_ready": state.index_ready if state else False,
            "parsed_papers_ready": bool(state and state.processed_count > 0),
            "papers_count": state.pdf_count if state else 0,
            "vector_count": state.vector_count if state else 0,
            "api_keys": {
                "deepseek": "DEEPSEEK_API_KEY" not in health.missing_keys,
                "dashscope": "DASHSCOPE_API_KEY" not in health.missing_keys,
                "mineru": True,
            },
        }
