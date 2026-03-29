"""Compatibility facade for corpus parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.exceptions import InsufficientPapersError, MineruParseError, NoPdfFoundError
from app.core.paths import PathManager
from app.infrastructure.parsing.mineru_client import MinerUClient
from app.use_cases.prepare_corpus import PrepareCorpusUseCase


def _build_paths(
    papers_dir: Optional[Path] = None,
    processed_dir: Optional[Path] = None,
) -> PathManager:
    settings = get_settings().model_copy(deep=True)
    if papers_dir is not None:
        settings.paths.papers_dir = str(papers_dir)
    if processed_dir is not None:
        settings.paths.processed_dir = str(processed_dir)
    return PathManager(settings_override=settings)


class ParserService:
    """Thin compatibility wrapper around `PrepareCorpusUseCase`."""

    def __init__(self, papers_dir: Optional[Path] = None, processed_dir: Optional[Path] = None):
        self._paths = _build_paths(papers_dir=papers_dir, processed_dir=processed_dir)
        self._use_case = PrepareCorpusUseCase(paths=self._paths)
        self._mineru = MinerUClient()
        self._settings = get_settings()

    @property
    def papers_dir(self) -> Path:
        return self._paths.papers_dir

    @property
    def processed_dir(self) -> Path:
        return self._paths.processed_dir

    @property
    def min_papers_for_review(self) -> int:
        return self._settings.pipeline.min_papers_for_review

    def count_pdf_files(self) -> int:
        if not self._paths.papers_dir.exists():
            return 0
        return len(list(self._paths.papers_dir.glob("*.pdf")))

    def count_processed_papers(self) -> int:
        if not self._paths.processed_dir.exists():
            return 0
        return len(
            [
                item
                for item in self._paths.processed_dir.iterdir()
                if item.is_dir() and (item / "content_list_v2.json").exists() and (item / "content_list_v2.json").stat().st_size > 0
            ]
        )

    def ensure_minimum_papers(self, min_required: Optional[int] = None) -> int:
        min_required = min_required or self.min_papers_for_review
        papers_count = self.count_pdf_files()
        if papers_count < min_required:
            raise InsufficientPapersError(
                papers_count=papers_count,
                min_required=min_required,
                papers_dir=str(self._paths.papers_dir),
            )
        return papers_count

    def has_parsed_papers(self) -> bool:
        return self.count_processed_papers() > 0

    def get_processed_papers(self) -> List[str]:
        if not self._paths.processed_dir.exists():
            return []
        return sorted(
            [
                item.name
                for item in self._paths.processed_dir.iterdir()
                if item.is_dir() and (item / "content_list_v2.json").exists()
            ]
        )

    def get_pdf_files(self) -> List[Path]:
        pdf_files = sorted(self._paths.papers_dir.glob("*.pdf")) if self._paths.papers_dir.exists() else []
        if not pdf_files:
            raise NoPdfFoundError(str(self._paths.papers_dir))
        return pdf_files

    def parse_all_papers(self) -> Dict[str, bool]:
        result = self._use_case.execute(force=False)
        return result.results

    def parse_single_paper(self, pdf_path: Path) -> bool:
        output_dir = self._paths.processed_dir / pdf_path.stem
        try:
            self._mineru.parse_pdf(pdf_path=pdf_path, output_dir=output_dir)
        except Exception as exc:
            raise MineruParseError(str(pdf_path), str(exc)) from exc
        content_path = output_dir / "content_list_v2.json"
        return content_path.exists() and content_path.stat().st_size > 0

    def ensure_parsed(self, force_reparse: bool = False, min_required: Optional[int] = None) -> bool:
        expected_pdf_count = self.ensure_minimum_papers(min_required)
        processed_count = self.count_processed_papers()
        if not force_reparse and processed_count >= expected_pdf_count:
            return True
        self._use_case.execute(force=force_reparse)
        return True
