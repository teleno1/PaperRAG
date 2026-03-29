from __future__ import annotations

from app.core.config import get_settings
from app.core.paths import PathManager, get_paths
from app.domain.models.runtime import HealthStatus, ProjectState
from app.use_cases._shared import build_faiss_repository


class HealthAndStateUseCase:
    def __init__(self, paths: PathManager | None = None) -> None:
        self._paths = paths or get_paths()
        self._repository = build_faiss_repository(paths=self._paths)

    def get_state(self) -> ProjectState:
        pdf_count = len(list(self._paths.papers_dir.glob("*.pdf"))) if self._paths.papers_dir.exists() else 0
        processed_count = len(
            [
                item
                for item in self._paths.processed_dir.iterdir()
                if item.is_dir() and (item / "content_list_v2.json").exists() and (item / "content_list_v2.json").stat().st_size > 0
            ]
        ) if self._paths.processed_dir.exists() else 0
        outlines_count = len(list(self._paths.outlines_dir.glob("*/outline.json"))) if self._paths.outlines_dir.exists() else 0
        latest_run_dir = None
        if self._paths.outputs_dir.exists():
            run_dirs = sorted([item for item in self._paths.outputs_dir.iterdir() if item.is_dir()], key=lambda path: path.stat().st_mtime, reverse=True)
            latest_run_dir = str(run_dirs[0]) if run_dirs else None
        return ProjectState(
            pdf_count=pdf_count,
            processed_count=processed_count,
            index_ready=self._repository.exists(),
            vector_count=self._repository.count() if self._repository.exists() else 0,
            outlines_count=outlines_count,
            latest_run_dir=latest_run_dir,
        )

    def get_health(self) -> HealthStatus:
        settings = get_settings()
        missing_keys: list[str] = []
        if not settings.models.deepseek_api_key:
            missing_keys.append("DEEPSEEK_API_KEY")
        if not settings.models.dashscope_api_key:
            missing_keys.append("DASHSCOPE_API_KEY")
        return HealthStatus(
            ok=not missing_keys,
            missing_keys=missing_keys,
            state=self.get_state(),
        )
