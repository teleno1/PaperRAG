"""General report routes."""

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.exceptions import PaperRAGError
from app.schemas import ErrorResponse, ReportRunRequest, ReportRunResponse
from app.use_cases.run_report import RunReportUseCase

router = APIRouter()


@router.post(
    "/report",
    response_model=ReportRunResponse,
    responses={"200": {"model": ReportRunResponse}, "400": {"model": ErrorResponse}},
)
async def run_report(request: ReportRunRequest) -> ReportRunResponse:
    use_case = RunReportUseCase()
    try:
        start_time = time.time()
        result = use_case.execute(
            query=request.query,
            output_format=request.output_format,
            top_k=request.top_k,
        )
        payload = result.model_dump(mode="json")
        payload["elapsed_time"] = time.time() - start_time
        return ReportRunResponse(**payload)
    except PaperRAGError as exc:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="report_run_failed",
                detail=str(exc),
                error_type=exc.__class__.__name__,
            ).model_dump(),
        )
