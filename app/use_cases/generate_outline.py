from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from app.core.exceptions import OutlineGenerationError
from app.core.paths import PathManager, get_paths
from app.domain.outline.planner import OutlinePlanner
from app.use_cases.build_index import BuildIndexUseCase
from app.use_cases._shared import build_retrieval_service, ensure_minimum_papers


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:50] if len(slug) > 50 else slug


class GenerateOutlineUseCase:
    def __init__(
        self,
        planner: OutlinePlanner | None = None,
        build_index_use_case: BuildIndexUseCase | None = None,
        paths: PathManager | None = None,
    ) -> None:
        self._paths = paths or get_paths()
        self._build_index = build_index_use_case or BuildIndexUseCase(paths=self._paths)
        self._planner = planner or OutlinePlanner(build_retrieval_service(paths=self._paths))

    def execute(self, topic: str, output_path: Path | None = None) -> Path:
        self._paths.ensure_dirs()
        ensure_minimum_papers(paths=self._paths)
        self._build_index.execute(force=False)
        if output_path is None:
            slug = f"{_slugify(topic)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_path = self._paths.outlines_dir / slug / "outline.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            outline = self._planner.plan(topic)
        except Exception as exc:
            raise OutlineGenerationError(topic, str(exc)) from exc

        output_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path
