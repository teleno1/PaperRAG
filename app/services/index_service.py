"""Compatibility facade for vector index operations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.paths import PathManager
from app.use_cases._shared import build_faiss_repository
from app.use_cases.build_index import BuildIndexUseCase
from app.use_cases.prepare_corpus import PrepareCorpusUseCase


def _build_paths(
    processed_dir: Optional[Path] = None,
    database_dir: Optional[Path] = None,
) -> PathManager:
    settings = get_settings().model_copy(deep=True)
    if processed_dir is not None:
        settings.paths.processed_dir = str(processed_dir)
    if database_dir is not None:
        settings.paths.database_dir = str(database_dir)
    return PathManager(settings_override=settings)


class IndexService:
    """Thin compatibility wrapper around `BuildIndexUseCase`."""

    def __init__(
        self,
        processed_dir: Optional[Path] = None,
        database_dir: Optional[Path] = None,
        parser_service=None,
    ):
        self._paths = _build_paths(processed_dir=processed_dir, database_dir=database_dir)
        self._prepare_corpus = PrepareCorpusUseCase(paths=self._paths)
        self._use_case = BuildIndexUseCase(
            prepare_corpus_use_case=self._prepare_corpus,
            paths=self._paths,
        )
        self._repository = build_faiss_repository(paths=self._paths)

    @property
    def database_dir(self) -> Path:
        return self._paths.database_dir

    @property
    def index_path(self) -> Path:
        return self._paths.faiss_index_path

    @property
    def metadata_path(self) -> Path:
        return self._paths.metadata_path

    def index_exists(self) -> bool:
        return self._repository.exists()

    def get_vector_count(self) -> int:
        return self._repository.count() if self._repository.exists() else 0

    def build_index(
        self,
        data_dir: Optional[Path] = None,
        force_reparse: bool = False,
        min_required: Optional[int] = None,
    ) -> int:
        if force_reparse:
            self._prepare_corpus.execute(force=True)
        result = self._use_case.execute(force=force_reparse or not self._repository.exists())
        return result.total_vectors

    def ensure_index(
        self,
        force_rebuild: bool = False,
        force_reparse: bool = False,
        min_required: Optional[int] = None,
    ) -> bool:
        if self._repository.exists() and not force_rebuild:
            return True
        self.build_index(force_reparse=force_reparse, min_required=min_required)
        return True

    def get_index_info(self) -> dict:
        return {
            "database_dir": str(self._paths.database_dir),
            "index_path": str(self._paths.faiss_index_path),
            "metadata_path": str(self._paths.metadata_path),
            "index_exists": self._repository.exists(),
            "vector_count": self.get_vector_count(),
        }

    def clear_index(self) -> None:
        self._paths.faiss_index_path.unlink(missing_ok=True)
        self._paths.metadata_path.unlink(missing_ok=True)
