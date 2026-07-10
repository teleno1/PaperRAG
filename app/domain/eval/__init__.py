"""Evaluation dataset models and helpers."""

from app.domain.eval.comparison import StrategyComparisonResult, StrategyComparisonRow, StrategyConfig
from app.domain.eval.loader import load_eval_dataset
from app.domain.eval.models import AnswerExpectation, EvalDataset, EvalDatasetRow, QuestionShape
from app.domain.eval.results import EvalCaseResult, EvalRunMetrics, EvalRunResult
from app.domain.eval.generation_metrics import (
    ABSTENTION_CUES,
    GenerationAggregateMetrics,
    GenerationCaseMetrics,
    aggregate_generation_metrics,
    answer_point_coverage,
    abstention_cue_present,
    build_generation_case_metrics,
    citation_hit_rate,
    format_compliance,
    no_source_assertion_rate,
    unsupported_aspect_violation_count,
    unknown_citation_count,
)
from app.domain.eval.retrieval_metrics import (
    RetrievalAggregateMetrics,
    RetrievalCaseMetrics,
    aggregate_retrieval_metrics,
    build_retrieval_case_metrics,
    mean_reciprocal_rank,
    recall_at_k,
)

__all__ = [
    "EvalDataset",
    "EvalDatasetRow",
    "EvalCaseResult",
    "EvalRunMetrics",
    "EvalRunResult",
    "AnswerExpectation",
    "QuestionShape",
    "StrategyComparisonResult",
    "StrategyComparisonRow",
    "StrategyConfig",
    "GenerationAggregateMetrics",
    "GenerationCaseMetrics",
    "ABSTENTION_CUES",
    "RetrievalAggregateMetrics",
    "RetrievalCaseMetrics",
    "aggregate_generation_metrics",
    "answer_point_coverage",
    "abstention_cue_present",
    "aggregate_retrieval_metrics",
    "build_generation_case_metrics",
    "build_retrieval_case_metrics",
    "citation_hit_rate",
    "format_compliance",
    "load_eval_dataset",
    "mean_reciprocal_rank",
    "no_source_assertion_rate",
    "recall_at_k",
    "unsupported_aspect_violation_count",
    "unknown_citation_count",
]
