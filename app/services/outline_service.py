"""Compatibility facade for outline generation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.exceptions import OutlineGenerationError
from app.core.paths import PathManager
from app.use_cases.generate_outline import GenerateOutlineUseCase


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower())
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:50]


def _build_paths(outlines_dir: Optional[Path] = None) -> PathManager:
    settings = get_settings().model_copy(deep=True)
    if outlines_dir is not None:
        settings.paths.outlines_dir = str(outlines_dir)
    return PathManager(settings_override=settings)


class OutlineService:
    """Thin compatibility wrapper around `GenerateOutlineUseCase`."""

    def __init__(
        self,
        outlines_dir: Optional[Path] = None,
        index_service=None,
        parser_service=None,
    ):
        self._paths = _build_paths(outlines_dir=outlines_dir)
        self._use_case = GenerateOutlineUseCase(paths=self._paths)

    @property
    def outlines_dir(self) -> Path:
        return self._paths.outlines_dir

    def generate_outline(
        self,
        topic: str,
        output_path: Optional[Path] = None,
        slug: Optional[str] = None,
    ) -> Path:
        if output_path is None and slug is not None:
            output_path = self._paths.outlines_dir / slug / "outline.json"
        return self._use_case.execute(topic=topic, output_path=output_path)

    def load_outline(self, outline_path: Path) -> dict:
        outline_path = Path(outline_path)
        if not outline_path.exists():
            raise OutlineGenerationError("", f"Outline file does not exist: {outline_path}")
        return json.loads(outline_path.read_text(encoding="utf-8"))

    def get_outline_info(self, outline_path: Path) -> dict:
        outline = self.load_outline(outline_path)
        sections_count = len(outline.get("sections", []))
        body_count = 0
        final_pass_count = 0
        for section in outline.get("sections", []):
            if section.get("write_stage", "body") == "body":
                body_count += 1
            else:
                final_pass_count += 1
        return {
            "title": outline.get("title", ""),
            "language": outline.get("language", "中文"),
            "sections_count": sections_count,
            "body_sections_count": body_count,
            "final_pass_sections_count": final_pass_count,
            "outline_path": str(outline_path),
        }

    def list_outlines(self) -> list[Path]:
        if not self._paths.outlines_dir.exists():
            return []
        return sorted(self._paths.outlines_dir.glob("*/outline.json"), key=lambda path: path.stat().st_mtime, reverse=True)
