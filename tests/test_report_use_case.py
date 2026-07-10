import json

from app.domain.report.models import ReportResult
from app.domain.retrieval.models import RetrievedSource
from app.use_cases.run_report import RunReportUseCase


class FakeRetrievalService:
    def search(self, query: str, top_k: int = 20):
        assert query == "Generate a portability report"
        assert top_k == 4
        return [
            RetrievedSource(
                source_id="chunk-1",
                document_id="doc-1",
                paper_id="doc-1",
                chunk_id="chunk-1",
                title="Portability Notes",
                section="overview",
                content="The system supports PDF, TXT, and Markdown ingestion.",
            ),
            RetrievedSource(
                source_id="chunk-2",
                document_id="doc-2",
                paper_id="doc-2",
                chunk_id="chunk-2",
                title="Validation Notes",
                section="trust",
                content="The system validates cited source ids against retrieved chunks.",
            ),
        ]


class FakeJsonClient:
    def __init__(self, payload):
        self.payload = payload

    def complete_json(self, prompt: str, temperature: float = 0.2, system_prompt: str | None = None):
        assert "Retrieved sources JSON" in prompt
        assert system_prompt
        return self.payload


def test_run_report_use_case_writes_markdown_artifacts(tmp_path):
    from tests.test_use_cases import _paths

    use_case = RunReportUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "title": "Portability Report",
                "overview": "A brief overview.",
                "sections": [
                    {
                        "title": "Coverage",
                        "body": "The system supports multiple document types.",
                        "cited_source_ids": ["chunk-1"],
                    },
                    {
                        "title": "Trust",
                        "body": "The system validates citations against retrieved chunks.",
                        "cited_source_ids": ["chunk-2"],
                    },
                ],
            }
        ),
        paths=_paths(tmp_path),
    )

    result = use_case.execute("Generate a portability report", output_format="markdown", top_k=4, run_id="report-1")

    assert isinstance(result, ReportResult)
    assert result.output_path.name == "report.md"
    assert result.output_path.exists()
    rendered = result.output_path.read_text(encoding="utf-8")
    assert "# Portability Report" in rendered
    assert "## Coverage" in rendered
    assert "[Sources: chunk-1]" in rendered
    assert result.report_json_path.exists()
    assert result.retrieved_sources_path.exists()
    assert result.validation_path.exists()


def test_run_report_use_case_writes_json_output(tmp_path):
    from tests.test_use_cases import _paths

    use_case = RunReportUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "title": "Portability Report",
                "overview": "A brief overview.",
                "sections": [
                    {
                        "title": "Coverage",
                        "body": "The system supports multiple document types.",
                        "cited_source_ids": ["chunk-1"],
                    }
                ],
            }
        ),
        paths=_paths(tmp_path),
    )

    result = use_case.execute("Generate a portability report", output_format="json", top_k=4, run_id="report-2")

    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert result.output_path.name == "report.json"
    assert payload["title"] == "Portability Report"
    assert payload["sections"][0]["cited_source_ids"] == ["chunk-1"]


def test_run_report_use_case_writes_bullet_summary_output(tmp_path):
    from tests.test_use_cases import _paths

    use_case = RunReportUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "title": "Portability Report",
                "overview": "A brief overview.",
                "sections": [
                    {
                        "title": "Coverage",
                        "body": "The system supports multiple document types.",
                        "cited_source_ids": ["chunk-1"],
                    }
                ],
            }
        ),
        paths=_paths(tmp_path),
    )

    result = use_case.execute("Generate a portability report", output_format="bullet_summary", top_k=4, run_id="report-3")

    rendered = result.output_path.read_text(encoding="utf-8")
    assert result.output_path.name == "report.bullet_summary.md"
    assert "- Coverage: The system supports multiple document types. [Sources: chunk-1]" in rendered


def test_run_report_use_case_flags_unknown_source_ids(tmp_path):
    from tests.test_use_cases import _paths

    use_case = RunReportUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "title": "Portability Report",
                "overview": "A brief overview.",
                "sections": [
                    {
                        "title": "Coverage",
                        "body": "The system supports multiple document types.",
                        "cited_source_ids": ["chunk-9"],
                    }
                ],
            }
        ),
        paths=_paths(tmp_path),
    )

    result = use_case.execute("Generate a portability report", output_format="markdown", top_k=4, run_id="report-4")

    assert result.validation.ok is False
    assert result.validation.unknown_source_ids == ["chunk-9"]
    assert result.report.sections[0].cited_source_ids == []
    rendered = result.output_path.read_text(encoding="utf-8")
    assert "chunk-9" not in rendered


def test_run_report_use_case_keeps_empty_citations_when_model_omits_them(tmp_path):
    from tests.test_use_cases import _paths

    use_case = RunReportUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "title": "Availability Report",
                "overview": "The provided sources do not document pricing.",
                "sections": [
                    {
                        "title": "Pricing",
                        "body": "The provided sources do not document pricing for this workflow.",
                        "cited_source_ids": [],
                    }
                ],
            }
        ),
        paths=_paths(tmp_path),
    )

    result = use_case.execute("Generate a portability report", output_format="bullet_summary", top_k=4, run_id="report-6")

    assert result.report.sections[0].cited_source_ids == []
    rendered = result.output_path.read_text(encoding="utf-8")
    assert "[Sources:" not in rendered


def test_run_report_use_case_strips_unknown_source_ids_from_json_output(tmp_path):
    from tests.test_use_cases import _paths

    use_case = RunReportUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "title": "Portability Report",
                "overview": "A brief overview.",
                "sections": [
                    {
                        "title": "Coverage",
                        "body": "The system supports multiple document types.",
                        "cited_source_ids": ["chunk-1", "chunk-9"],
                    }
                ],
            }
        ),
        paths=_paths(tmp_path),
    )

    result = use_case.execute("Generate a portability report", output_format="json", top_k=4, run_id="report-5")

    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload["sections"][0]["cited_source_ids"] == ["chunk-1"]


def test_run_report_use_case_coerces_summary_details_payload(tmp_path):
    from tests.test_use_cases import _paths

    use_case = RunReportUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "summary": "The provided sources do not document pricing.",
                "details": "The corpus covers ingestion and validation, but not pricing.",
            }
        ),
        paths=_paths(tmp_path),
    )

    result = use_case.execute("Generate a portability report", output_format="json", top_k=4, run_id="report-7")

    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload["title"].startswith("Report:")
    assert payload["overview"] == "The provided sources do not document pricing."
    assert payload["sections"][0]["title"] == "Details"
