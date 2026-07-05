import json

import pytest

from app.core.exceptions import PaperRAGError
from app.domain.eval import EvalDataset, EvalDatasetRow
from app.use_cases.run_eval import RunEvalUseCase


def _paths(tmp_path):
    from tests.test_use_cases import _paths as build_paths

    paths = build_paths(tmp_path)
    settings = getattr(paths, "_settings")
    settings.paths.eval_outputs_dir = str(tmp_path / "eval_outputs")
    return paths


class FakeTimer:
    def __init__(self, values):
        self._values = iter(values)

    def __call__(self):
        return next(self._values)


class FakeReportUseCase:
    def execute(self, query, output_format="markdown", top_k=None, run_id=None):
        from app.domain.answer.models import AnswerValidation
        from app.domain.report.models import GeneratedReport, ReportResult, ReportSection
        from app.domain.retrieval.models import RetrievedSource

        if query == "Success case":
            return ReportResult(
                run_id=run_id or "case-success",
                run_dir="F:/tmp/case-success",
                query=query,
                output_format="markdown",
                output_path="F:/tmp/case-success/report.md",
                report_json_path="F:/tmp/case-success/report.json",
                retrieved_sources_path="F:/tmp/case-success/retrieved_sources.json",
                validation_path="F:/tmp/case-success/validation.json",
                content="# Success Report\n\n## Coverage\nSupports traceable ids. [Sources: chunk-1]",
                report=GeneratedReport(
                    title="Success Report",
                    overview="Overview",
                    sections=[ReportSection(title="Coverage", body="Supports traceable ids.", cited_source_ids=["chunk-1"])],
                ),
                retrieved_sources=[
                    RetrievedSource(
                        source_id="chunk-1",
                        document_id="product_notes",
                        paper_id="product_notes",
                        chunk_id="chunk-1",
                        title="Product Notes",
                        section="overview",
                        content="Supports traceable ids.",
                    )
                ],
                validation=AnswerValidation(
                    ok=True,
                    cited_source_ids=["chunk-1"],
                    available_source_ids=["chunk-1"],
                ),
            )

        if query == "Unknown citation case":
            return ReportResult(
                run_id=run_id or "case-unknown",
                run_dir="F:/tmp/case-unknown",
                query=query,
                output_format="bullet_summary",
                output_path="F:/tmp/case-unknown/report.bullet_summary.md",
                report_json_path="F:/tmp/case-unknown/report.json",
                retrieved_sources_path="F:/tmp/case-unknown/retrieved_sources.json",
                validation_path="F:/tmp/case-unknown/validation.json",
                content="- Retrieval coverage stays deterministic. [Sources: unknown]",
                report=GeneratedReport(
                    title="Unknown Citation Report",
                    overview="Overview",
                    sections=[
                        ReportSection(
                            title="Coverage",
                            body="Retrieval coverage stays deterministic.",
                            cited_source_ids=["unknown"],
                        )
                    ],
                ),
                retrieved_sources=[
                    RetrievedSource(
                        source_id="chunk-2",
                        document_id="retrieval_playbook",
                        paper_id="retrieval_playbook",
                        chunk_id="chunk-2",
                        title="Retrieval Playbook",
                        section="testing",
                        content="Use deterministic corpora.",
                    )
                ],
                validation=AnswerValidation(
                    ok=False,
                    cited_source_ids=["unknown"],
                    available_source_ids=["chunk-2"],
                    unknown_source_ids=["unknown"],
                ),
            )

        raise RuntimeError("synthetic eval failure")


def fake_dataset_loader(path):
    assert str(path).endswith("eval_dataset.jsonl")
    return EvalDataset(
        rows=[
            EvalDatasetRow(
                id="case-1",
                query="Success case",
                expected_sources=["product_notes"],
                answer_points=["traceability"],
                output_format="markdown",
            ),
            EvalDatasetRow(
                id="case-2",
                query="Unknown citation case",
                expected_sources=["retrieval_playbook"],
                answer_points=["deterministic tests"],
                output_format="bullet_summary",
            ),
            EvalDatasetRow(
                id="case-3",
                query="Runtime failure case",
                expected_sources=["retrieval_playbook"],
                answer_points=["failure handling"],
                output_format="json",
            ),
        ]
    )


def test_run_eval_use_case_writes_artifacts(tmp_path):
    use_case = RunEvalUseCase(
        dataset_loader=fake_dataset_loader,
        report_use_case=FakeReportUseCase(),
        paths=_paths(tmp_path),
        timer=FakeTimer([0.0, 0.01, 1.0, 1.03, 2.0, 2.05]),
    )

    result = use_case.execute("data/eval_samples/eval_dataset.jsonl", run_id="eval-run-1")

    assert result.run_dir == use_case._paths.eval_outputs_dir / "eval-run-1"
    assert result.metrics_path.exists()
    assert result.cases_path.exists()
    assert result.failures_path.exists()
    assert result.retrieval_debug_path.exists()
    assert result.case_count == 3
    assert result.failure_count == 2
    assert result.metrics.failure_rate == 2 / 3
    assert result.metrics.generation.unknown_citation_count == 1
    assert result.metrics.avg_latency_ms == pytest.approx(30.0)
    assert result.metrics.p95_latency_ms == pytest.approx(48.0)

    metrics_payload = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics_payload["case_count"] == 3
    assert metrics_payload["failure_count"] == 2
    assert metrics_payload["metrics"]["avg_latency_ms"] == pytest.approx(30.0)

    cases_rows = [json.loads(line) for line in result.cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(cases_rows) == 3
    assert cases_rows[0]["retrieval_metrics"]["recall_at_5"] == 1.0
    assert cases_rows[0]["retrieval_metrics"]["mrr"] == 1.0
    assert cases_rows[0]["retrieval_metrics"]["retrieved_source_count"] == 1
    assert cases_rows[0]["latency_ms"] == pytest.approx(10.0)
    assert cases_rows[1]["latency_ms"] == pytest.approx(30.0)
    assert cases_rows[2]["latency_ms"] == pytest.approx(50.0)

    failures_rows = [json.loads(line) for line in result.failures_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(failures_rows) == 2

    retrieval_debug_rows = [
        json.loads(line) for line in result.retrieval_debug_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(retrieval_debug_rows) == 3
    assert retrieval_debug_rows[0]["expected_source_ids"] == ["product_notes"]
    assert retrieval_debug_rows[0]["retrieval_metric_ids"] == ["product_notes"]
    assert retrieval_debug_rows[0]["retrieved_sources"][0]["document_id"] == "product_notes"


def test_run_eval_use_case_default_report_runner_uses_current_paths(monkeypatch, tmp_path):
    captured = {}

    class FakeDefaultReportUseCase:
        def __init__(self, retrieval_service=None, llm_client=None, paths=None):
            captured["retrieval_service"] = retrieval_service
            captured["llm_client"] = llm_client
            captured["paths"] = paths

    monkeypatch.setattr("app.use_cases.run_eval.RunReportUseCase", FakeDefaultReportUseCase)

    use_case = RunEvalUseCase(paths=_paths(tmp_path))
    report_use_case = use_case._get_report_use_case(use_case._paths.get_eval_output_dir("eval-run-1"))

    assert captured["retrieval_service"] is None
    assert captured["llm_client"] is None
    assert report_use_case is not None
    assert captured["paths"].database_dir == use_case._paths.database_dir
    assert captured["paths"].outputs_dir == use_case._paths.get_eval_output_dir("eval-run-1") / "case_outputs"


def test_run_eval_use_case_wraps_setup_failures(tmp_path):
    def broken_loader(path):
        raise ValueError("broken setup")

    use_case = RunEvalUseCase(
        dataset_loader=broken_loader,
        report_use_case=FakeReportUseCase(),
        paths=_paths(tmp_path),
    )

    with pytest.raises(PaperRAGError) as exc_info:
        use_case.execute("data/eval_samples/eval_dataset.jsonl", run_id="eval-run-2")

    assert "Evaluation setup failed." in str(exc_info.value)
