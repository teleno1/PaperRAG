"""Evaluation routes."""

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.exceptions import PaperRAGError
from app.schemas import ErrorResponse, EvalRunRequest, EvalRunResponse
from app.use_cases.run_eval import RunEvalUseCase

router = APIRouter()


@router.post(
    "/eval/run",
    response_model=EvalRunResponse,
    responses={"200": {"model": EvalRunResponse}, "400": {"model": ErrorResponse}},
)
async def run_eval(request: EvalRunRequest) -> EvalRunResponse:
    use_case = RunEvalUseCase()
    try:
        start_time = time.time()
        result = use_case.execute(
            dataset=request.dataset,
            top_k=request.top_k,
        )
        payload = result.model_dump(mode="json")
        payload["elapsed_time"] = time.time() - start_time
        return EvalRunResponse(**payload)
    except PaperRAGError as exc:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="eval_run_failed",
                detail=str(exc),
                error_type=exc.__class__.__name__,
            ).model_dump(),
        )
