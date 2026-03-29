"""Health routes."""

from fastapi import APIRouter

from app.schemas import HealthResponse
from app.use_cases.health_and_state import HealthAndStateUseCase

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    use_case = HealthAndStateUseCase()
    health = use_case.get_health()
    state = health.state
    return HealthResponse(
        status="ok" if health.ok else "error",
        database_ready=bool(state and state.index_ready),
        parsed_papers_ready=bool(state and state.processed_count > 0),
        papers_count=state.pdf_count if state else 0,
        vector_count=state.vector_count if state else 0,
        missing_keys=health.missing_keys,
    )
