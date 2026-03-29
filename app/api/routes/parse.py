"""Corpus preparation routes."""

from fastapi import APIRouter, HTTPException

from app.core.exceptions import PaperRAGError
from app.schemas import ErrorResponse, ParseRunRequest, ParseRunResponse
from app.use_cases.prepare_corpus import PrepareCorpusUseCase

router = APIRouter()


@router.post(
    "/prepare",
    response_model=ParseRunResponse,
    responses={
        "200": {"model": ParseRunResponse},
        "400": {"model": ErrorResponse},
        "500": {"model": ErrorResponse},
    },
)
async def prepare_corpus(request: ParseRunRequest) -> ParseRunResponse:
    use_case = PrepareCorpusUseCase()
    try:
        result = use_case.execute(force=request.force)
        return ParseRunResponse(
            papers_dir=str(result.papers_dir),
            processed_dir=str(result.processed_dir),
            total_papers=result.total_papers,
            successful=result.successful,
            failed=result.failed,
            results=result.results,
        )
    except PaperRAGError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
