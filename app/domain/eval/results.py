from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from app.domain.eval.generation_metrics import GenerationAggregateMetrics, GenerationCaseMetrics
from app.domain.eval.models import AnswerExpectation, EvalOutputFormat, QuestionShape
from app.domain.eval.retrieval_metrics import RetrievalAggregateMetrics, RetrievalCaseMetrics


class EvalCaseResult(BaseModel):
    case_id: str
    query: str
    answer_expectation: AnswerExpectation = "full_answer"
    question_shape: QuestionShape = "single_hop"
    expected_source_ids: list[str] = Field(default_factory=list)
    answer_points: list[str] = Field(default_factory=list)
    unsupported_aspects: list[str] = Field(default_factory=list)
    retrieved_source_ids: list[str] = Field(default_factory=list)
    cited_source_ids: list[str] = Field(default_factory=list)
    output_format: EvalOutputFormat
    report_run_id: str = ""
    output_path: str = ""
    latency_ms: float = 0.0
    passed: bool = False
    failure_label: str | None = None
    error: str | None = None
    retrieval_metrics: RetrievalCaseMetrics
    generation_metrics: GenerationCaseMetrics


class EvalRunMetrics(BaseModel):
    retrieval: RetrievalAggregateMetrics
    generation: GenerationAggregateMetrics
    avg_latency_ms: float
    p95_latency_ms: float
    failure_rate: float


class EvalRunResult(BaseModel):
    run_id: str
    run_dir: Path
    dataset_path: Path
    case_count: int
    failure_count: int
    metrics_path: Path
    cases_path: Path
    failures_path: Path
    retrieval_debug_path: Path
    metrics: EvalRunMetrics
    cases: list[EvalCaseResult] = Field(default_factory=list)
