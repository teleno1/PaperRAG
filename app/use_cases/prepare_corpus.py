from __future__ import annotations

from pathlib import Path

from app.core.exceptions import MineruParseError, NoPdfFoundError
from app.core.paths import PathManager, get_paths
from app.domain.models.runtime import PrepareCorpusResult
from app.infrastructure.parsing.mineru_client import MinerUClient


class PrepareCorpusUseCase:
    def __init__(
        self,
        mineru_client: MinerUClient | None = None,
        paths: PathManager | None = None,
    ) -> None:
        self._paths = paths or get_paths()
        self._mineru = mineru_client or MinerUClient()

    def execute(self, force: bool = False) -> PrepareCorpusResult:
        self._paths.ensure_dirs()
        pdf_files = sorted(self._paths.papers_dir.glob("*.pdf"))
        if not pdf_files:
            raise NoPdfFoundError(str(self._paths.papers_dir))

        results: dict[str, bool] = {}
        for pdf_path in pdf_files:
            output_dir = self._paths.processed_dir / pdf_path.stem
            content_path = output_dir / "content_list_v2.json"
            if not force and content_path.exists() and content_path.stat().st_size > 0:
                results[pdf_path.name] = True
                continue
            try:
                self._mineru.parse_pdf(pdf_path=pdf_path, output_dir=output_dir)
                results[pdf_path.name] = content_path.exists() and content_path.stat().st_size > 0
            except Exception as exc:
                results[pdf_path.name] = False
                raise MineruParseError(str(pdf_path), str(exc)) from exc

        successful = sum(1 for ok in results.values() if ok)
        failed = len(results) - successful
        return PrepareCorpusResult(
            papers_dir=self._paths.papers_dir,
            processed_dir=self._paths.processed_dir,
            total_papers=len(results),
            successful=successful,
            failed=failed,
            results=results,
        )

