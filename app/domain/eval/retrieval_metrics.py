from __future__ import annotations

from pydantic import BaseModel


def _normalize_ids(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def recall_at_k(retrieved_source_ids: list[str], expected_source_ids: list[str], k: int) -> float:
    expected = set(_normalize_ids(expected_source_ids))
    if not expected or k <= 0:
        return 0.0
    retrieved = _normalize_ids(retrieved_source_ids)[:k]
    return 1.0 if any(source_id in expected for source_id in retrieved) else 0.0


def mean_reciprocal_rank(retrieved_source_ids: list[str], expected_source_ids: list[str]) -> float:
    expected = set(_normalize_ids(expected_source_ids))
    if not expected:
        return 0.0
    for rank, source_id in enumerate(_normalize_ids(retrieved_source_ids), start=1):
        if source_id in expected:
            return 1.0 / rank
    return 0.0


class RetrievalCaseMetrics(BaseModel):
    recall_at_5: float
    recall_at_10: float
    mrr: float
    retrieved_source_count: int


class RetrievalAggregateMetrics(BaseModel):
    recall_at_5: float
    recall_at_10: float
    mrr: float
    avg_retrieved_sources: float
    case_count: int


def build_retrieval_case_metrics(
    retrieved_source_ids: list[str],
    expected_source_ids: list[str],
) -> RetrievalCaseMetrics:
    normalized_retrieved = _normalize_ids(retrieved_source_ids)
    return RetrievalCaseMetrics(
        recall_at_5=recall_at_k(normalized_retrieved, expected_source_ids, 5),
        recall_at_10=recall_at_k(normalized_retrieved, expected_source_ids, 10),
        mrr=mean_reciprocal_rank(normalized_retrieved, expected_source_ids),
        retrieved_source_count=len(normalized_retrieved),
    )


def aggregate_retrieval_metrics(case_metrics: list[RetrievalCaseMetrics]) -> RetrievalAggregateMetrics:
    if not case_metrics:
        return RetrievalAggregateMetrics(
            recall_at_5=0.0,
            recall_at_10=0.0,
            mrr=0.0,
            avg_retrieved_sources=0.0,
            case_count=0,
        )

    case_count = len(case_metrics)
    return RetrievalAggregateMetrics(
        recall_at_5=sum(item.recall_at_5 for item in case_metrics) / case_count,
        recall_at_10=sum(item.recall_at_10 for item in case_metrics) / case_count,
        mrr=sum(item.mrr for item in case_metrics) / case_count,
        avg_retrieved_sources=sum(item.retrieved_source_count for item in case_metrics) / case_count,
        case_count=case_count,
    )
