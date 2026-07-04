"""General query routes."""

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.exceptions import PaperRAGError
from app.schemas import ErrorResponse, QueryRunRequest, QueryRunResponse
from app.use_cases.run_query import RunQueryUseCase

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryRunResponse,
    responses={"200": {"model": QueryRunResponse}, "400": {"model": ErrorResponse}},
)
async def run_query(request: QueryRunRequest) -> QueryRunResponse:
    use_case = RunQueryUseCase()
    try:
        start_time = time.time()
        result = use_case.execute(
            query=request.query,
            top_k=request.top_k,
            include_retrieved_sources=request.include_retrieved_sources,
        )
        payload = result.model_dump(mode="json")
        payload["elapsed_time"] = time.time() - start_time
        return QueryRunResponse(**payload)
    except PaperRAGError as exc:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="query_run_failed",
                detail=str(exc),
                error_type=exc.__class__.__name__,
            ).model_dump(),
        )
