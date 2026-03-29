"""API request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    database_ready: bool
    parsed_papers_ready: bool
    papers_count: int = 0
    vector_count: int = 0
    missing_keys: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ParseRunRequest(BaseModel):
    force: bool = Field(default=False, description="Force reparsing existing papers")


class ParseRunResponse(BaseModel):
    papers_dir: str
    processed_dir: str
    total_papers: int
    successful: int
    failed: int
    results: dict[str, bool]


class IndexBuildRequest(BaseModel):
    force: bool = Field(default=False, description="Force rebuild index")


class IndexBuildResponse(BaseModel):
    database_dir: str
    index_path: str
    metadata_path: str
    total_vectors: int
    elapsed_time: float


class OutlineGenerateRequest(BaseModel):
    topic: str = Field(..., description="Review topic", min_length=2)
    save_path: Optional[str] = Field(default=None, description="Optional custom output path")


class OutlineGenerateResponse(BaseModel):
    topic: str
    outline_path: str
    sections_count: int


class ReviewRunRequest(BaseModel):
    topic: str = Field(..., description="Review topic", min_length=2)
    ensure_index: bool = Field(default=True, description="Ensure corpus and index before running")


class ReviewRunFromOutlineRequest(BaseModel):
    outline_path: str = Field(..., description="Path to outline.json")


class ReviewRunResponse(BaseModel):
    outline_path: str
    run_dir: str
    final_review_md: str
    final_review_txt: str
    final_review_json: str
    references_json: str
    validation_report: str
    elapsed_time: float


class StateResponse(BaseModel):
    papers_dir: str
    papers_count: int
    processed_dir: str
    processed_count: int
    database_dir: str
    database_ready: bool
    index_path: Optional[str] = None
    metadata_path: Optional[str] = None
    vector_count: int = 0
    outlines_count: int = 0
    latest_run_dir: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    error_type: Optional[str] = None
