from fastapi.testclient import TestClient

from app.api.main import app
from app.domain.answer.models import AnswerResult, AnswerValidation
from app.domain.eval import EvalRunMetrics, EvalRunResult, GenerationAggregateMetrics, RetrievalAggregateMetrics
from app.domain.report.models import GeneratedReport, ReportResult, ReportSection
from app.domain.retrieval.models import RetrievedSource
from app.domain.models.runtime import ReviewRunResult


def test_state_route(monkeypatch):
    from app.api.routes import pipeline as pipeline_route

    class FakeUseCase:
        def get_state(self):
            from app.domain.models.runtime import ProjectState

            return ProjectState(
                pdf_count=1,
                processed_count=1,
                index_ready=True,
                vector_count=10,
                outlines_count=2,
                latest_run_dir="/tmp/run1",
            )

    monkeypatch.setattr(pipeline_route, "HealthAndStateUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.get("/state")
    assert response.status_code == 200
    assert response.json()["vector_count"] == 10


def test_review_run_from_outline_route(monkeypatch):
    from app.api.routes import review as review_route

    class FakeUseCase:
        def execute(self, outline_path):
            return ReviewRunResult(
                run_id="run-1",
                run_dir=outline_path.parent / "run-1",
                outline_path=outline_path,
                final_review_md=outline_path.parent / "run-1/07_export/final_review.md",
                final_review_txt=outline_path.parent / "run-1/07_export/final_review.txt",
                final_review_json=outline_path.parent / "run-1/07_export/final_review.json",
                references_json=outline_path.parent / "run-1/07_export/references.json",
                validation_report=outline_path.parent / "run-1/06_validation/validation_report.json",
            )

    monkeypatch.setattr(review_route, "RunReviewFromOutlineUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.post("/review/run-from-outline", json={"outline_path": __file__})
    assert response.status_code == 200
    assert response.json()["run_dir"].endswith("run-1")


def test_query_route(monkeypatch):
    from app.api.routes import query as query_route

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

    monkeypatch.setattr(query_route, "RunQueryUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.post("/query", json={"query": "What changed?", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["cited_source_ids"] == ["chunk-1"]
    assert payload["retrieved_sources"][0]["document_id"] == "doc-1"


def test_report_route(monkeypatch):
    from app.api.routes import report as report_route

    class FakeUseCase:
        def execute(self, query, output_format="markdown", top_k=None):
            assert query == "Generate report"
            assert output_format == "markdown"
            assert top_k == 4
            return ReportResult(
                run_id="report-1",
                run_dir="F:/tmp/report-1",
                query=query,
                output_format="markdown",
                output_path="F:/tmp/report-1/report.md",
                report_json_path="F:/tmp/report-1/report.json",
                retrieved_sources_path="F:/tmp/report-1/retrieved_sources.json",
                validation_path="F:/tmp/report-1/validation.json",
                content="# Report",
                report=GeneratedReport(
                    title="Report",
                    overview="Overview",
                    sections=[
                        ReportSection(
                            title="Coverage",
                            body="The system supports multiple document types.",
                            cited_source_ids=["chunk-1"],
                        )
                    ],
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

    monkeypatch.setattr(report_route, "RunReportUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.post("/report", json={"query": "Generate report", "output_format": "markdown", "top_k": 4})
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "report-1"
    assert payload["report"]["sections"][0]["cited_source_ids"] == ["chunk-1"]


def test_eval_route(monkeypatch):
    from app.api.routes import eval as eval_route

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
                        answer_point_coverage=0.85,
                        unsupported_aspect_violation_count=0,
                        abstention_cue_rate=0.1,
                        case_count=3,
                    ),
                    avg_latency_ms=12.5,
                    p95_latency_ms=20.0,
                    failure_rate=1 / 3,
                ),
            )

    monkeypatch.setattr(eval_route, "RunEvalUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.post("/eval/run", json={"dataset": "data/eval_samples/eval_dataset.jsonl", "top_k": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "eval-1"
    assert payload["metrics"]["generation"]["format_compliance_rate"] == 1.0


def test_query_route_returns_error_response(monkeypatch):
    from app.api.routes import query as query_route
    from app.core.exceptions import PaperRAGError

    class FakeUseCase:
        def execute(self, query, top_k=None, include_retrieved_sources=True):
            raise PaperRAGError("boom")

    monkeypatch.setattr(query_route, "RunQueryUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.post("/query", json={"query": "What changed?"})
    assert response.status_code == 400
    assert response.json()["error"] == "query_run_failed"
    assert response.json()["detail"] == "boom"


def test_report_route_returns_error_response(monkeypatch):
    from app.api.routes import report as report_route
    from app.core.exceptions import PaperRAGError

    class FakeUseCase:
        def execute(self, query, output_format="markdown", top_k=None):
            raise PaperRAGError("boom")

    monkeypatch.setattr(report_route, "RunReportUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.post("/report", json={"query": "Generate report"})
    assert response.status_code == 400
    assert response.json()["error"] == "report_run_failed"
    assert response.json()["detail"] == "boom"


def test_eval_route_returns_error_response(monkeypatch):
    from app.api.routes import eval as eval_route
    from app.core.exceptions import PaperRAGError

    class FakeUseCase:
        def execute(self, dataset, top_k=None):
            raise PaperRAGError("boom")

    monkeypatch.setattr(eval_route, "RunEvalUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.post("/eval/run", json={"dataset": "data/eval_samples/eval_dataset.jsonl"})
    assert response.status_code == 400
    assert response.json()["error"] == "eval_run_failed"
    assert response.json()["detail"] == "boom"
