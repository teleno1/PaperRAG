from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import ApiKeyMissingError, InsufficientPapersError, NoPdfFoundError
from app.core.paths import PathManager, get_paths
from app.infrastructure.retrieval.faiss_recall_service import FaissRecallService
from app.infrastructure.vectorstore.faiss_repository import FaissRepository


def build_faiss_repository(paths: PathManager | None = None) -> FaissRepository:
    path_manager = paths or get_paths()
    return FaissRepository(
        index_path=path_manager.faiss_index_path,
        metadata_path=path_manager.metadata_path,
    )


def build_retrieval_service(paths: PathManager | None = None) -> FaissRecallService:
    return FaissRecallService(repository=build_faiss_repository(paths=paths))


def build_run_id() -> str:
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"


def ensure_minimum_papers(paths: PathManager | None = None) -> int:
    path_manager = paths or get_paths()
    settings = getattr(path_manager, "_settings", None) or get_settings()
    min_required = max(settings.pipeline.min_papers_for_review, 1)

    pdf_count = len(list(path_manager.papers_dir.glob("*.pdf"))) if path_manager.papers_dir.exists() else 0
    processed_count = (
        len(
            [
                item
                for item in path_manager.processed_dir.iterdir()
                if item.is_dir()
                and (item / "content_list_v2.json").exists()
                and (item / "content_list_v2.json").stat().st_size > 0
            ]
        )
        if path_manager.processed_dir.exists()
        else 0
    )
    available_count = max(pdf_count, processed_count)

    if available_count == 0:
        raise NoPdfFoundError(str(path_manager.papers_dir))
    if available_count < min_required:
        raise InsufficientPapersError(
            papers_count=available_count,
            min_required=min_required,
            papers_dir=str(path_manager.papers_dir),
        )
    return available_count


def ensure_required_keys(include_mineru: bool = False) -> None:
    settings = get_settings()
    missing_keys: list[str] = []
    if not settings.models.deepseek_api_key:
        missing_keys.append("DEEPSEEK_API_KEY")
    if not settings.models.dashscope_api_key:
        missing_keys.append("DASHSCOPE_API_KEY")
    if include_mineru and not settings.models.mineru_api_key:
        missing_keys.append("MINERU_API_KEY")
    if missing_keys:
        raise ApiKeyMissingError(", ".join(missing_keys))
