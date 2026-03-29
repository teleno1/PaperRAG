"""Index routes."""

import time

from fastapi import APIRouter, HTTPException

from app.core.exceptions import PaperRAGError
from app.schemas import ErrorResponse, IndexBuildRequest, IndexBuildResponse
from app.use_cases.build_index import BuildIndexUseCase

router = APIRouter()


@router.post(
    "/build",
    response_model=IndexBuildResponse,
    responses={"200": {"model": IndexBuildResponse}, "400": {"model": ErrorResponse}},
)
async def build_index(request: IndexBuildRequest) -> IndexBuildResponse:
    use_case = BuildIndexUseCase()
    try:
        start_time = time.time()
        result = use_case.execute(force=request.force)
        return IndexBuildResponse(
            database_dir=str(result.database_dir),
            index_path=str(result.index_path),
            metadata_path=str(result.metadata_path),
            total_vectors=result.total_vectors,
            elapsed_time=time.time() - start_time,
        )
    except PaperRAGError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
