"""Compatibility facade for review pipeline execution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.paths import PathManager
from app.use_cases.run_review_from_outline import RunReviewFromOutlineUseCase


def _build_paths(outputs_dir: Optional[Path] = None) -> PathManager:
    settings = get_settings().model_copy(deep=True)
    if outputs_dir is not None:
        settings.paths.outputs_dir = str(outputs_dir)
    return PathManager(settings_override=settings)


class ReviewService:
    """Thin compatibility wrapper around `RunReviewFromOutlineUseCase`."""

    def __init__(
        self,
        outputs_dir: Optional[Path] = None,
        index_service=None,
        parser_service=None,
    ):
        self._paths = _build_paths(outputs_dir=outputs_dir)
        self._use_case = RunReviewFromOutlineUseCase(paths=self._paths)

    @property
    def outputs_dir(self) -> Path:
        return self._paths.outputs_dir

    def run_review(
        self,
        outline_path: Path,
        output_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
    ) -> dict:
        use_case = self._use_case if output_dir is None else RunReviewFromOutlineUseCase(paths=_build_paths(output_dir))
        result = use_case.execute(outline_path=Path(outline_path), run_id=run_id)
        return {
            "outline_path": str(result.outline_path),
            "run_dir": str(result.run_dir),
            "final_review_md": str(result.final_review_md),
            "final_review_txt": str(result.final_review_txt),
            "final_review_json": str(result.final_review_json),
            "references_json": str(result.references_json),
            "validation_report": str(result.validation_report),
        }

    def get_run_output_dir(self, run_id: str) -> Path:
        return self._paths.outputs_dir / run_id

    def list_runs(self) -> list[dict]:
        if not self._paths.outputs_dir.exists():
            return []
        runs = []
        for run_dir in self._paths.outputs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            run_info = {
                "run_id": run_dir.name,
                "path": str(run_dir),
                "created": datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat(),
            }
            export_dir = run_dir / "07_export"
            if export_dir.exists():
                run_info["has_output"] = True
                run_info["final_review_md"] = str(export_dir / "final_review.md")
            else:
                run_info["has_output"] = False
            runs.append(run_info)
        return sorted(runs, key=lambda item: item["created"], reverse=True)

    def get_run_result(self, run_id: str) -> Optional[dict]:
        run_dir = self.get_run_output_dir(run_id)
        if not run_dir.exists():
            return None
        export_dir = run_dir / "07_export"
        validation_dir = run_dir / "06_validation"
        result = {"run_id": run_id, "run_dir": str(run_dir)}
        if export_dir.exists():
            result["final_review_md"] = str(export_dir / "final_review.md")
            result["final_review_txt"] = str(export_dir / "final_review.txt")
            result["final_review_json"] = str(export_dir / "final_review.json")
            result["references_json"] = str(export_dir / "references.json")
        if validation_dir.exists():
            result["validation_report"] = str(validation_dir / "validation_report.json")
        return result
