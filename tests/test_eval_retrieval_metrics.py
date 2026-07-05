from app.domain.eval.retrieval_metrics import (
    aggregate_retrieval_metrics,
    build_retrieval_case_metrics,
    mean_reciprocal_rank,
    recall_at_k,
)


def test_recall_at_k_hits_when_expected_source_is_in_top_k() -> None:
    assert recall_at_k(["s1", "s2", "s3"], ["s2"], 5) == 1.0
    assert recall_at_k(["s1", "s2", "s3"], ["s2"], 1) == 0.0


def test_recall_at_k_returns_zero_for_empty_expected_or_retrieval() -> None:
    assert recall_at_k([], ["s2"], 5) == 0.0
    assert recall_at_k(["s1"], [], 5) == 0.0


def test_retrieval_metrics_ignore_duplicate_retrieved_ids() -> None:
    metrics = build_retrieval_case_metrics(
        retrieved_source_ids=["s1", "s1", "s2", "s2", "s3"],
        expected_source_ids=["s2"],
    )

    assert metrics.recall_at_5 == 1.0
    assert metrics.recall_at_10 == 1.0
    assert metrics.mrr == 0.5
    assert metrics.retrieved_source_count == 3


def test_recall_at_k_deduplicates_before_applying_top_k_boundary() -> None:
    assert recall_at_k(["s1", "s1", "s2"], ["s2"], 2) == 1.0
    assert mean_reciprocal_rank(["s1", "s1", "s2"], ["s2"]) == 0.5


def test_mean_reciprocal_rank_returns_zero_when_expected_source_is_missing() -> None:
    assert mean_reciprocal_rank(["s1", "s2"], ["s9"]) == 0.0
    assert mean_reciprocal_rank(["s1", "s2"], []) == 0.0


def test_aggregate_retrieval_metrics_is_deterministic() -> None:
    cases = [
        build_retrieval_case_metrics(["s1", "s2"], ["s2"]),
        build_retrieval_case_metrics(["s3"], ["s9"]),
    ]

    metrics = aggregate_retrieval_metrics(cases)

    assert metrics.case_count == 2
    assert metrics.recall_at_5 == 0.5
    assert metrics.recall_at_10 == 0.5
    assert metrics.mrr == 0.25
    assert metrics.avg_retrieved_sources == 1.5
