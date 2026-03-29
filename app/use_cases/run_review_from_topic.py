from __future__ import annotations

from app.core.paths import PathManager, get_paths
from app.domain.models.runtime import ReviewRunResult
from app.use_cases.build_index import BuildIndexUseCase
from app.use_cases.generate_outline import GenerateOutlineUseCase
from app.use_cases.run_review_from_outline import RunReviewFromOutlineUseCase


class RunReviewFromTopicUseCase:
    def __init__(
        self,
        build_index_use_case: BuildIndexUseCase | None = None,
        generate_outline_use_case: GenerateOutlineUseCase | None = None,
        run_review_from_outline_use_case: RunReviewFromOutlineUseCase | None = None,
        paths: PathManager | None = None,
    ) -> None:
        self._paths = paths or get_paths()
        self._build_index = build_index_use_case or BuildIndexUseCase(paths=self._paths)
        self._generate_outline = generate_outline_use_case or GenerateOutlineUseCase(paths=self._paths)
        self._run_review_from_outline = run_review_from_outline_use_case or RunReviewFromOutlineUseCase(paths=self._paths)

    def execute(self, topic: str, ensure_index: bool = True) -> ReviewRunResult:
        if ensure_index:
            self._build_index.execute(force=False)
        outline_path = self._generate_outline.execute(topic)
        return self._run_review_from_outline.execute(outline_path=outline_path)

