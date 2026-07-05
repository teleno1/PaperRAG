import json
from argparse import Namespace

from app.domain.answer.models import AnswerResult, AnswerValidation
from app.domain.eval import (
    EvalRunMetrics,
    EvalRunResult,
    GenerationAggregateMetrics,
    RetrievalAggregateMetrics,
    StrategyComparisonResult,
    StrategyComparisonRow,
)
from app.domain.report.models import GeneratedReport, ReportResult, ReportSection
from app.domain.retrieval.models import RetrievedSource


def test_cmd_query_run(monkeypatch, capsys):
    from app.cli import main as cli_main

    class FakeUseCase:
        def execute(self, query, top_k=None, include_retrieved_sources=True):
            assert query == "What changed?"
            assert top_k == 3
            assert include_retrieved_sources is True
            return AnswerResult(
                query=query,
                answer_text="A cited answer.",
                cited_source_ids=["chunk-1"],
                retrieved_sources=[
                    RetrievedSource(
                        source_id="chunk-1",
                        document_id="doc-1",
                        paper_id="doc-1",
                        chunk_id="chunk-1",
                        title="Architecture",
                        section="overview",
                        content="Grounded content.",
                    )
                ],
                validation=AnswerValidation(
                    ok=True,
                    cited_source_ids=["chunk-1"],
                    available_source_ids=["chunk-1"],
                ),
            )

    monkeypatch.setattr(cli_main, "RunQueryUseCase", FakeUseCase)
    code = cli_main.cmd_query_run(Namespace(query="What changed?", top_k=3, hide_sources=False))

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["cited_source_ids"] == ["chunk-1"]
    assert payload["retrieved_sources"][0]["document_id"] == "doc-1"


def test_cmd_report_run(monkeypatch, capsys):
    from app.cli import main as cli_main

    class FakeUseCase:
        def execute(self, query, output_format="markdown", top_k=None):
            assert query == "Generate report"
            assert output_format == "json"
            assert top_k == 4
            return ReportResult(
                run_id="report-1",
                run_dir="F:/tmp/report-1",
                query=query,
                output_format="json",
                output_path="F:/tmp/report-1/report.json",
                report_json_path="F:/tmp/report-1/report.json",
                retrieved_sources_path="F:/tmp/report-1/retrieved_sources.json",
                validation_path="F:/tmp/report-1/validation.json",
                content="{\"title\":\"Report\"}",
                report=GeneratedReport(
                    title="Report",
                    overview="Overview",
                    sections=[ReportSection(title="Coverage", body="Portable", cited_source_ids=["chunk-1"])],
                ),
                retrieved_sources=[
                    RetrievedSource(
                        source_id="chunk-1",
                        document_id="doc-1",
                        paper_id="doc-1",
                        chunk_id="chunk-1",
                        title="Architecture",
                        section="overview",
                        content="Grounded content.",
                    )
                ],
                validation=AnswerValidation(
                    ok=True,
                    cited_source_ids=["chunk-1"],
                    available_source_ids=["chunk-1"],
                ),
            )

    monkeypatch.setattr(cli_main, "RunReportUseCase", FakeUseCase)
    code = cli_main.cmd_report_run(Namespace(query="Generate report", format="json", top_k=4))

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["run_id"] == "report-1"
    assert payload["output_format"] == "json"


def test_cmd_eval_run(monkeypatch, capsys):
    from app.cli import main as cli_main

    class FakeUseCase:
        def execute(self, dataset, top_k=None):
            assert dataset == "data/eval_samples/eval_dataset.jsonl"
            assert top_k == 5
            return EvalRunResult(
                run_id="eval-1",
                run_dir="F:/tmp/eval-1",
                dataset_path="data/eval_samples/eval_dataset.jsonl",
                case_count=3,
                failure_count=1,
                metrics_path="F:/tmp/eval-1/metrics.json",
                cases_path="F:/tmp/eval-1/cases.jsonl",
                failures_path="F:/tmp/eval-1/failures.jsonl",
                retrieval_debug_path="F:/tmp/eval-1/retrieval_debug.jsonl",
                metrics=EvalRunMetrics(
                    retrieval=RetrievalAggregateMetrics(
                        recall_at_5=1.0,
                        recall_at_10=1.0,
                        mrr=0.8,
                        avg_retrieved_sources=2.0,
                        case_count=3,
                    ),
                    generation=GenerationAggregateMetrics(
                        citation_hit_rate=0.9,
                        unknown_citation_count=0,
                        format_compliance_rate=1.0,
                        no_source_assertion_rate=0.1,
                        case_count=3,
                    ),
                    avg_latency_ms=12.5,
                    p95_latency_ms=20.0,
                    failure_rate=1 / 3,
                ),
            )

    monkeypatch.setattr(cli_main, "RunEvalUseCase", FakeUseCase)
    code = cli_main.cmd_eval_run(Namespace(dataset="data/eval_samples/eval_dataset.jsonl", top_k=5))

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["run_id"] == "eval-1"
    assert payload["metrics"]["retrieval"]["recall_at_5"] == 1.0


def test_cmd_eval_compare(monkeypatch, capsys):
    from app.cli import main as cli_main

    class FakeUseCase:
        def execute(self, dataset, source_dir):
            assert dataset == "data/eval_samples/eval_dataset.jsonl"
            assert source_dir == "data/samples/phase2_corpus"
            return StrategyComparisonResult(
                run_id="compare-1",
                run_dir="F:/tmp/compare-1",
                dataset_path="data/eval_samples/eval_dataset.jsonl",
                source_dir="data/samples/phase2_corpus",
                comparison_path="F:/tmp/compare-1/comparison.json",
                summary_table="strategy_id | chunking | top_k | rerank",
                strategies=[
                    StrategyComparisonRow(
                        strategy_id="balanced_topk3_rerank_on",
                        chunking_preset="balanced",
                        top_k=3,
                        rerank_mode="on",
                        run_dir="F:/tmp/compare-1/strategies/balanced_topk3_rerank_on",
                        case_count=3,
                        failure_count=0,
                        metrics=EvalRunMetrics(
                            retrieval=RetrievalAggregateMetrics(
                                recall_at_5=1.0,
                                recall_at_10=1.0,
                                mrr=0.8,
                                avg_retrieved_sources=3.0,
                                case_count=3,
                            ),
                            generation=GenerationAggregateMetrics(
                                citation_hit_rate=0.9,
                                unknown_citation_count=0,
                                format_compliance_rate=1.0,
                                no_source_assertion_rate=0.1,
                                case_count=3,
                            ),
                            avg_latency_ms=12.0,
                            p95_latency_ms=15.0,
                            failure_rate=0.0,
                        ),
                    )
                ],
            )

    monkeypatch.setattr(cli_main, "RunEvalStrategyComparisonUseCase", FakeUseCase)
    code = cli_main.cmd_eval_compare(
        Namespace(dataset="data/eval_samples/eval_dataset.jsonl", source_dir="data/samples/phase2_corpus")
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["run_id"] == "compare-1"


def test_query_parser_without_subcommand_prints_help(capsys):
    from app.cli.main import build_parser

    parser = build_parser()
    args = parser.parse_args(["query"])
    code = args.func(args)

    output = capsys.readouterr().out
    assert code == 0
    assert "Run a cited answer query" in output


def test_eval_parser_without_subcommand_prints_help(capsys):
    from app.cli.main import build_parser

    parser = build_parser()
    args = parser.parse_args(["eval"])
    code = args.func(args)

    output = capsys.readouterr().out
    assert code == 0
    assert "Run evaluation over a dataset" in output


def test_eval_compare_parser_routes_to_compare_handler():
    from app.cli.main import build_parser, cmd_eval_compare

    parser = build_parser()
    args = parser.parse_args(["eval", "compare", "--dataset", "data/eval_samples/eval_dataset.jsonl"])

    assert args.func == cmd_eval_compare
    assert args.source_dir == "data/samples/phase2_corpus"


def test_report_parser_without_subcommand_prints_help(capsys):
    from app.cli.main import build_parser

    parser = build_parser()
    args = parser.parse_args(["report"])
    code = args.func(args)

    output = capsys.readouterr().out
    assert code == 0
    assert "Run a cited report request" in output
