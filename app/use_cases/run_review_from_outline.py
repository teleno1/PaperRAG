from __future__ import annotations

import shutil
from pathlib import Path

from app.core.exceptions import ReviewPipelineError
from app.core.paths import PathManager, get_paths
from app.domain.models.runtime import ReviewRunResult
from app.domain.review.engine import ReviewPipelineEngine
from app.domain.review.outline_loader import build_execution_plan, dump_json, load_outline, normalize_outline
from app.use_cases._shared import build_retrieval_service, build_run_id, ensure_minimum_papers


class RunReviewFromOutlineUseCase:
    def __init__(
        self,
        engine: ReviewPipelineEngine | None = None,
        paths: PathManager | None = None,
    ) -> None:
        self._paths = paths or get_paths()
        self._engine = engine or ReviewPipelineEngine(build_retrieval_service(paths=self._paths))

    def execute(self, outline_path: Path, run_id: str | None = None) -> ReviewRunResult:
        outline_path = Path(outline_path)
        if not outline_path.exists():
            raise ReviewPipelineError(stage="init", reason=f"Outline file does not exist: {outline_path}", outline_path=str(outline_path))

        ensure_minimum_papers(paths=self._paths)
        run_id = run_id or build_run_id()
        run_dir = self._paths.outputs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        try:
            raw_outline = load_outline(outline_path)
            normalized_outline = normalize_outline(raw_outline)
            plan = build_execution_plan(raw_outline)
            outline_stage_dir = run_dir / "00_outline"
            outline_stage_dir.mkdir(parents=True, exist_ok=True)
            dump_json(normalized_outline, outline_stage_dir / "normalized_outline.json")
            shutil.copy2(outline_path, outline_stage_dir / "outline.json")
            result = self._engine.run(plan=plan, run_dir=run_dir)
        except ReviewPipelineError:
            raise
        except Exception as exc:
            raise ReviewPipelineError(stage="pipeline", reason=str(exc), outline_path=str(outline_path)) from exc

        return result
