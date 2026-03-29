"""Review routes."""

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.exceptions import PaperRAGError
from app.schemas import (
    ErrorResponse,
    ReviewRunFromOutlineRequest,
    ReviewRunRequest,
    ReviewRunResponse,
)
from app.use_cases.run_review_from_outline import RunReviewFromOutlineUseCase
from app.use_cases.run_review_from_topic import RunReviewFromTopicUseCase

router = APIRouter()


def _to_response(result, elapsed_time: float) -> ReviewRunResponse:
    return ReviewRunResponse(
        outline_path=str(result.outline_path),
        run_dir=str(result.run_dir),
        final_review_md=str(result.final_review_md),
        final_review_txt=str(result.final_review_txt),
        final_review_json=str(result.final_review_json),
        references_json=str(result.references_json),
        validation_report=str(result.validation_report),
        elapsed_time=elapsed_time,
    )


@router.post(
    "/run",
    response_model=ReviewRunResponse,
    responses={"200": {"model": ReviewRunResponse}, "400": {"model": ErrorResponse}},
)
async def run_review(request: ReviewRunRequest) -> ReviewRunResponse:
    use_case = RunReviewFromTopicUseCase()
    try:
        start_time = time.time()
        result = use_case.execute(topic=request.topic, ensure_index=request.ensure_index)
        return _to_response(result, time.time() - start_time)
    except PaperRAGError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/run-from-outline",
    response_model=ReviewRunResponse,
    responses={"200": {"model": ReviewRunResponse}, "400": {"model": ErrorResponse}},
)
async def run_review_from_outline(request: ReviewRunFromOutlineRequest) -> ReviewRunResponse:
    use_case = RunReviewFromOutlineUseCase()
    outline_path = Path(request.outline_path)
    if not outline_path.exists():
        raise HTTPException(status_code=400, detail=f"Outline file does not exist: {outline_path}")
    try:
        start_time = time.time()
        result = use_case.execute(outline_path=outline_path)
        return _to_response(result, time.time() - start_time)
    except PaperRAGError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
