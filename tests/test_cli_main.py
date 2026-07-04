import json
from argparse import Namespace

from app.domain.answer.models import AnswerResult, AnswerValidation
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


def test_query_parser_without_subcommand_prints_help(capsys):
    from app.cli.main import build_parser

    parser = build_parser()
    args = parser.parse_args(["query"])
    code = args.func(args)

    output = capsys.readouterr().out
    assert code == 0
    assert "Run a cited answer query" in output


def test_report_parser_without_subcommand_prints_help(capsys):
    from app.cli.main import build_parser

    parser = build_parser()
    args = parser.parse_args(["report"])
    code = args.func(args)

    output = capsys.readouterr().out
    assert code == 0
    assert "Run a cited report request" in output
