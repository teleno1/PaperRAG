"""API request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

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


class RetrievedSourceResponse(BaseModel):
    source_id: str
    document_id: str = ""
    paper_id: str = ""
    chunk_id: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: str = ""
    venue: str = ""
    section: str = ""
    content: str
    paper_score: Optional[float] = None
    chunk_score: Optional[float] = None


class AnswerValidationResponse(BaseModel):
    ok: bool = True
    cited_source_ids: list[str] = Field(default_factory=list)
    available_source_ids: list[str] = Field(default_factory=list)
    unknown_source_ids: list[str] = Field(default_factory=list)
    duplicate_source_ids: list[str] = Field(default_factory=list)


class QueryRunRequest(BaseModel):
    query: str = Field(..., description="User query", min_length=2)
    top_k: Optional[int] = Field(default=None, description="Optional retrieval depth override")
    include_retrieved_sources: bool = Field(default=True, description="Return retrieved source content in the response")


class QueryRunResponse(BaseModel):
    query: str
    answer_text: str
    cited_source_ids: list[str] = Field(default_factory=list)
    retrieved_sources: list[RetrievedSourceResponse] = Field(default_factory=list)
    validation: AnswerValidationResponse
    elapsed_time: float


class ReportSectionResponse(BaseModel):
    title: str
    body: str
    cited_source_ids: list[str] = Field(default_factory=list)


class GeneratedReportResponse(BaseModel):
    title: str
    overview: str = ""
    sections: list[ReportSectionResponse] = Field(default_factory=list)


class ReportRunRequest(BaseModel):
    query: str = Field(..., description="Report request", min_length=2)
    output_format: Literal["markdown", "json", "bullet_summary"] = Field(default="markdown")
    top_k: Optional[int] = Field(default=None, description="Optional retrieval depth override")


class ReportRunResponse(BaseModel):
    run_id: str
    run_dir: str
    query: str
    output_format: Literal["markdown", "json", "bullet_summary"]
    output_path: str
    report_json_path: str
    retrieved_sources_path: str
    validation_path: str
    content: str
    report: GeneratedReportResponse
    retrieved_sources: list[RetrievedSourceResponse] = Field(default_factory=list)
    validation: AnswerValidationResponse
    elapsed_time: float


class RetrievalMetricsResponse(BaseModel):
    recall_at_5: float
    recall_at_10: float
    mrr: float
    avg_retrieved_sources: float
    case_count: int


class GenerationMetricsResponse(BaseModel):
    citation_hit_rate: float
    unknown_citation_count: int
    format_compliance_rate: float
    no_source_assertion_rate: float
    answer_point_coverage: float
    unsupported_aspect_violation_count: int
    abstention_cue_rate: float
    case_count: int


class EvalMetricsResponse(BaseModel):
    retrieval: RetrievalMetricsResponse
    generation: GenerationMetricsResponse
    avg_latency_ms: float
    p95_latency_ms: float
    failure_rate: float


class EvalRunRequest(BaseModel):
    dataset: str = Field(..., description="Path to the eval dataset JSONL file", min_length=1)
    top_k: Optional[int] = Field(default=None, description="Optional retrieval depth override for every eval case")


class EvalRunResponse(BaseModel):
    run_id: str
    run_dir: str
    dataset_path: str
    case_count: int
    failure_count: int
    metrics_path: str
    cases_path: str
    failures_path: str
    retrieval_debug_path: str
    metrics: EvalMetricsResponse
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
    next_action: Optional[str] = None


class OutlineSectionRequest(BaseModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = ""


class OutlineSectionResponse(BaseModel):
    id: str
    title: str
    description: str = ""


class ReportOutlineResponse(BaseModel):
    id: str
    workspace_id: str
    revision_number: int
    status: Literal["draft", "approved"]
    title: str
    research_question: str
    sections: list[OutlineSectionResponse] = Field(default_factory=list)
    evidence_paper_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    approved_at: Optional[str] = None


class OutlineSaveRequest(BaseModel):
    revision_id: Optional[str] = None
    title: str = Field(..., min_length=1)
    research_question: str = Field(..., min_length=1)
    sections: list[OutlineSectionRequest] = Field(..., min_length=1)


class OutlineApproveRequest(BaseModel):
    revision_id: str = Field(..., min_length=1)


class WorkspaceCreateRequest(BaseModel):
    topic: str = Field(..., min_length=2, description="Research topic")
    report_language: Literal["zh", "en"] = Field(default="zh", description="Literature Report language")


class WorkspaceOperationResponse(BaseModel):
    id: str
    workspace_id: str
    paper_id: Optional[str] = None
    operation_type: str
    status: Literal["queued", "running", "succeeded", "failed", "interrupted", "cancelled"]
    phase: str
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    retry_action: Optional[str] = None
    completed_work: int = 0
    total_work: int = 1
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ResearchPaperResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    source_kind: Literal["upload", "discovery"]
    original_filename: str
    selected: bool
    evidence_readiness: Literal[
        "awaiting_authorised_file",
        "importing",
        "parsing",
        "indexing",
        "ready",
        "failed",
        "unavailable",
    ]
    evidence_eligible: bool
    active_document_version_id: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    year: str = ""
    venue: str = ""
    failure_phase: Optional[str] = None
    failure_message: Optional[str] = None
    retryable: bool = False
    next_action: Optional[str] = None
    doi: Optional[str] = None
    abstract: str = ""
    published_at: Optional[str] = None
    source_updated_at: Optional[str] = None
    source_url: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_urls: list[str] = Field(default_factory=list)
    is_open_access: Optional[bool] = None
    license: Optional[str] = None
    source_links: list[str] = Field(default_factory=list)
    discovery_query: Optional[str] = None
    discovered_at: Optional[str] = None
    dismissed: bool = False


class ResearchWorkspaceResponse(BaseModel):
    id: str
    topic: str
    report_language: Literal["zh", "en"]
    state: Literal["setup", "active", "archived"]
    created_at: str
    updated_at: str
    papers: list[ResearchPaperResponse] = Field(default_factory=list)
    operations: list[WorkspaceOperationResponse] = Field(default_factory=list)
    outline: Optional[ReportOutlineResponse] = None


class WorkspaceUploadResponse(BaseModel):
    paper: ResearchPaperResponse
    operation: Optional[WorkspaceOperationResponse] = None


class WorkspaceDiscoveryRequest(BaseModel):
    query: Optional[str] = Field(default=None, min_length=2, description="Topic search query")
    provider: Literal["openalex", "arxiv"] = Field(default="openalex", description="Discovery provider")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=50)


class WorkspaceDiscoveryResponse(BaseModel):
    provider: Literal["openalex", "arxiv"]
    query: str
    status: Literal["succeeded", "empty", "retryable_error", "failed"]
    candidates: list[ResearchPaperResponse] = Field(default_factory=list)
    page: int = 1
    per_page: int = 10
    total_count: Optional[int] = None
    next_page: Optional[int] = None
    error_message: Optional[str] = None
    retryable: bool = False
    retry_after_seconds: Optional[int] = None
    next_action: Optional[str] = None
