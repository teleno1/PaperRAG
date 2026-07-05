import json

from app.domain.eval import EvalRunMetrics, GenerationAggregateMetrics, RetrievalAggregateMetrics, StrategyConfig
from app.use_cases.run_eval_comparison import (
    RunEvalStrategyComparisonUseCase,
    build_chunk_builder_for_preset,
    build_default_strategy_configs,
)


def _paths(tmp_path):
    from tests.test_use_cases import _paths as build_paths

    paths = build_paths(tmp_path)
    settings = getattr(paths, "_settings")
    settings.paths.eval_outputs_dir = str(tmp_path / "eval_outputs")
    return paths


def fake_strategy_runner(*, dataset, comparison_root, source_dir, strategy):
    from app.domain.eval import EvalRunResult

    score_boost = 0.1 if strategy.chunking_preset == "fine_grained" else 0.0
    top_k_boost = 0.1 if strategy.top_k == 5 else 0.0
    rerank_boost = 0.05 if strategy.rerank_mode == "on" else 0.0
    recall = 0.5 + score_boost + top_k_boost
    citation_hit_rate = 0.6 + rerank_boost
    return EvalRunResult(
        run_id=strategy.strategy_id,
        run_dir=comparison_root / "strategies" / strategy.strategy_id,
        dataset_path=dataset,
        case_count=3,
        failure_count=0 if strategy.rerank_mode == "on" else 1,
        metrics_path=comparison_root / "strategies" / strategy.strategy_id / "metrics.json",
        cases_path=comparison_root / "strategies" / strategy.strategy_id / "cases.jsonl",
        failures_path=comparison_root / "strategies" / strategy.strategy_id / "failures.jsonl",
        retrieval_debug_path=comparison_root / "strategies" / strategy.strategy_id / "retrieval_debug.jsonl",
        metrics=EvalRunMetrics(
            retrieval=RetrievalAggregateMetrics(
                recall_at_5=recall,
                recall_at_10=recall,
                mrr=0.4 + top_k_boost,
                avg_retrieved_sources=float(strategy.top_k),
                case_count=3,
            ),
            generation=GenerationAggregateMetrics(
                citation_hit_rate=citation_hit_rate,
                unknown_citation_count=0,
                format_compliance_rate=1.0,
                no_source_assertion_rate=0.0,
                case_count=3,
            ),
            avg_latency_ms=10.0,
            p95_latency_ms=15.0,
            failure_rate=0.0 if strategy.rerank_mode == "on" else (1 / 3),
        ),
    )


def test_build_chunk_builder_for_presets_changes_chunk_budget():
    balanced = build_chunk_builder_for_preset("balanced")
    fine_grained = build_chunk_builder_for_preset("fine_grained")

    assert balanced.max_tokens == 500
    assert balanced.overlap_sentences == 2
    assert fine_grained.max_tokens == 250
    assert fine_grained.overlap_sentences == 1
    assert fine_grained.min_unit_len < balanced.min_unit_len


def test_build_default_strategy_configs_covers_required_dimensions():
    configs = build_default_strategy_configs()

    assert {config.chunking_preset for config in configs} == {"balanced", "fine_grained"}
    assert {config.top_k for config in configs} == {3, 5}
    assert {config.rerank_mode for config in configs} == {"on", "off"}


def test_run_eval_strategy_comparison_writes_comparison_artifact(tmp_path):
    use_case = RunEvalStrategyComparisonUseCase(
        paths=_paths(tmp_path),
        strategy_runner=fake_strategy_runner,
    )

    result = use_case.execute(
        dataset="data/eval_samples/eval_dataset.jsonl",
        source_dir="data/samples/phase2_corpus",
        run_id="compare-1",
        strategy_configs=build_default_strategy_configs(),
    )

    assert result.run_dir == use_case._paths.eval_outputs_dir / "compare-1"
    assert result.comparison_path.exists()
    assert len(result.strategies) == 8
    assert "strategy_id | chunking | top_k | rerank" in result.summary_table
    assert any(row.chunking_preset == "fine_grained" for row in result.strategies)
    assert any(row.top_k == 5 for row in result.strategies)
    assert any(row.rerank_mode == "off" for row in result.strategies)

    payload = json.loads(result.comparison_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "compare-1"
    assert len(payload["strategies"]) == 8
    assert payload["strategies"][0]["metrics"]["retrieval"]["avg_retrieved_sources"] in {3.0, 5.0}


def test_build_strategy_report_use_case_applies_preset_and_disables_rerank(monkeypatch, tmp_path):
    captured = {}

    class FakeIndexBuilder:
        def __init__(self, chunk_builder):
            captured["chunk_builder"] = chunk_builder

        def build_from_source_dir(self, source_dir):
            captured["source_dir"] = source_dir
            return [[1.0]], [
                {
                    "document_id": "doc-1",
                    "paper_id": "doc-1",
                    "chunk_id": "chunk-1",
                    "title": "Doc 1",
                    "authors": [],
                    "year": "",
                    "venue": "",
                    "section": "Intro",
                    "content": "Chunk 1",
                }
            ]

    class FakeReportUseCase:
        def __init__(self, retrieval_service=None, paths=None, llm_client=None):
            captured["retrieval_service"] = retrieval_service
            captured["paths"] = paths
            captured["llm_client"] = llm_client

    monkeypatch.setattr("app.use_cases.run_eval_comparison.IndexBuilder", FakeIndexBuilder)
    monkeypatch.setattr("app.use_cases.run_eval_comparison.RunReportUseCase", FakeReportUseCase)

    use_case = RunEvalStrategyComparisonUseCase(paths=_paths(tmp_path))
    strategy = StrategyConfig(
        strategy_id="fine_grained_topk5_rerank_off",
        chunking_preset="fine_grained",
        top_k=5,
        rerank_mode="off",
    )
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    use_case._build_strategy_report_use_case(
        comparison_root=use_case._paths.eval_outputs_dir / "compare-1",
        strategy=strategy,
        source_dir=source_dir,
    )

    assert captured["chunk_builder"].max_tokens == 250
    assert captured["chunk_builder"].overlap_sentences == 1
    assert captured["retrieval_service"]._enable_rerank is False
    assert captured["paths"].outputs_dir.name == "case_outputs"
