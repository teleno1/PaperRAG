from __future__ import annotations

from app.core.exceptions import IndexBuildError
from app.core.paths import PathManager, get_paths
from app.domain.models.runtime import BuildIndexResult
from app.infrastructure.vectorstore.index_builder import IndexBuilder
from app.use_cases._shared import build_faiss_repository
from app.use_cases.prepare_corpus import PrepareCorpusUseCase


class BuildIndexUseCase:
    def __init__(
        self,
        index_builder: IndexBuilder | None = None,
        prepare_corpus_use_case: PrepareCorpusUseCase | None = None,
        paths: PathManager | None = None,
    ) -> None:
        self._paths = paths or get_paths()
        self._index_builder = index_builder or IndexBuilder()
        self._prepare_corpus = prepare_corpus_use_case or PrepareCorpusUseCase(paths=self._paths)
        self._repository = build_faiss_repository(paths=self._paths)

    def execute(self, force: bool = False) -> BuildIndexResult:
        self._paths.ensure_dirs()
        has_processed_corpus = any(self._paths.processed_dir.glob("*/content_list_v2.json"))
        if not has_processed_corpus:
            self._prepare_corpus.execute(force=force)

        if not force and self._repository.exists():
            total_vectors = self._repository.count()
        else:
            try:
                vectors, metadata = self._index_builder.build(self._paths.processed_dir)
                self._repository.save(vectors=vectors, metadata=metadata)
                total_vectors = self._repository.count()
            except Exception as exc:
                raise IndexBuildError(str(exc), str(self._paths.processed_dir)) from exc

        return BuildIndexResult(
            database_dir=self._paths.database_dir,
            index_path=self._paths.faiss_index_path,
            metadata_path=self._paths.metadata_path,
            total_vectors=total_vectors,
        )
