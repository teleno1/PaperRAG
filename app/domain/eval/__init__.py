"""Evaluation dataset models and helpers."""

from app.domain.eval.loader import load_eval_dataset
from app.domain.eval.models import EvalDataset, EvalDatasetRow
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
    "RetrievalAggregateMetrics",
    "RetrievalCaseMetrics",
    "aggregate_retrieval_metrics",
    "build_retrieval_case_metrics",
    "load_eval_dataset",
    "mean_reciprocal_rank",
    "recall_at_k",
]
