from pathlib import Path

from app.core.config import get_settings
from app.core.paths import PathManager
from app.use_cases.health_and_state import HealthAndStateUseCase


def _paths(tmp_path) -> PathManager:
    settings = get_settings().model_copy(deep=True)
    settings.paths.papers_dir = str(tmp_path / "papers")
    settings.paths.processed_dir = str(tmp_path / "processed")
    settings.paths.database_dir = str(tmp_path / "database")
    settings.paths.outlines_dir = str(tmp_path / "outlines")
    settings.paths.outputs_dir = str(tmp_path / "review_outputs")
    return PathManager(settings_override=settings)


def test_health_state_prefers_actual_report_run_dir(tmp_path):
    paths = _paths(tmp_path)
    paths.ensure_dirs()
    legacy_run_dir = paths.outputs_dir / "run-legacy"
    legacy_run_dir.mkdir(parents=True, exist_ok=True)
    report_run_dir = paths.outputs_dir / "reports" / "run-report"
    report_run_dir.mkdir(parents=True, exist_ok=True)

    report_marker = report_run_dir / "report.md"
    report_marker.write_text("report", encoding="utf-8")

    state = HealthAndStateUseCase(paths=paths).get_state()

    assert state.latest_run_dir == str(report_run_dir)
