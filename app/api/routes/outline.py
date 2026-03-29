"""Outline routes."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.exceptions import PaperRAGError
from app.schemas import ErrorResponse, OutlineGenerateRequest, OutlineGenerateResponse
from app.use_cases.generate_outline import GenerateOutlineUseCase

router = APIRouter()


@router.post(
    "/generate",
    response_model=OutlineGenerateResponse,
    responses={
        "200": {"model": OutlineGenerateResponse},
        "400": {"model": ErrorResponse},
        "500": {"model": ErrorResponse},
    },
)
async def generate_outline(request: OutlineGenerateRequest) -> OutlineGenerateResponse:
    use_case = GenerateOutlineUseCase()
    try:
        outline_path = use_case.execute(
            topic=request.topic,
            output_path=Path(request.save_path) if request.save_path else None,
        )
        content = json.loads(Path(outline_path).read_text(encoding="utf-8"))
        sections_count = len(content.get("sections", []))
        return OutlineGenerateResponse(
            topic=request.topic,
            outline_path=str(outline_path),
            sections_count=max(sections_count, 0),
        )
    except PaperRAGError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
