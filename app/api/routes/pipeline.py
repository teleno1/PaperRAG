"""State routes."""

from fastapi import APIRouter

from app.schemas import StateResponse
from app.use_cases.health_and_state import HealthAndStateUseCase
from app.core.paths import get_paths

router = APIRouter()


@router.get("/state", response_model=StateResponse)
async def get_state() -> StateResponse:
    use_case = HealthAndStateUseCase()
    state = use_case.get_state()
    paths = get_paths()
    return StateResponse(
        papers_dir=str(paths.papers_dir),
        papers_count=state.pdf_count,
        processed_dir=str(paths.processed_dir),
        processed_count=state.processed_count,
        database_dir=str(paths.database_dir),
        database_ready=state.index_ready,
        index_path=str(paths.faiss_index_path) if state.index_ready else None,
        metadata_path=str(paths.metadata_path) if state.index_ready else None,
        vector_count=state.vector_count,
        outlines_count=state.outlines_count,
        latest_run_dir=state.latest_run_dir,
    )
