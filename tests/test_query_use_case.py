from app.domain.answer.models import AnswerResult
from app.domain.retrieval.models import RetrievedSource
from app.use_cases.run_query import RunQueryUseCase


class FakeRetrievalService:
    def search(self, query: str, top_k: int = 20):
        assert query == "What changed in the architecture?"
        assert top_k == 3
        return [
            RetrievedSource(
                source_id="chunk-1",
                document_id="doc-architecture",
                paper_id="doc-architecture",
                chunk_id="chunk-1",
                title="Architecture",
                section="validation",
                content="The system validates source ids against retrieved sources.",
            ),
            RetrievedSource(
                source_id="chunk-2",
                document_id="doc-readme",
                paper_id="doc-readme",
                chunk_id="chunk-2",
                title="README",
                section="query",
                content="The query surface returns cited answers.",
            ),
        ]


class FakeJsonClient:
    def __init__(self, payload):
        self.payload = payload

    def complete_json(self, prompt: str, temperature: float = 0.2, system_prompt: str | None = None):
        assert "Retrieved sources JSON" in prompt
        assert system_prompt
        return self.payload


def test_run_query_use_case_returns_cited_answer():
    use_case = RunQueryUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "answer_text": "The architecture now validates cited source ids against retrieved chunks.",
                "cited_source_ids": ["chunk-1", "chunk-2"],
            }
        ),
    )

    result = use_case.execute("What changed in the architecture?", top_k=3)

    assert isinstance(result, AnswerResult)
    assert result.answer_text
    assert result.cited_source_ids == ["chunk-1", "chunk-2"]
    assert [source.document_id for source in result.retrieved_sources] == ["doc-architecture", "doc-readme"]
    assert result.validation.ok is True


def test_run_query_use_case_flags_unknown_citations():
    use_case = RunQueryUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "answer_text": "This answer cites an unknown source.",
                "cited_source_ids": ["chunk-1", "unknown-source"],
            }
        ),
    )

    result = use_case.execute("What changed in the architecture?", top_k=3)

    assert result.cited_source_ids == ["chunk-1", "unknown-source"]
    assert result.validation.ok is False
    assert result.validation.unknown_source_ids == ["unknown-source"]


def test_run_query_use_case_can_hide_retrieved_sources():
    use_case = RunQueryUseCase(
        retrieval_service=FakeRetrievalService(),
        llm_client=FakeJsonClient(
            {
                "answer_text": "Grounded answer.",
                "cited_source_ids": ["chunk-1", "chunk-1", "chunk-2"],
            }
        ),
    )

    result = use_case.execute(
        "What changed in the architecture?",
        top_k=3,
        include_retrieved_sources=False,
    )

    assert [source.source_id for source in result.retrieved_sources] == ["chunk-1", "chunk-2"]
    assert all(source.content == "" for source in result.retrieved_sources)
    assert result.cited_source_ids == ["chunk-1", "chunk-2"]
    assert result.validation.duplicate_source_ids == ["chunk-1"]


def test_run_query_use_case_uses_configured_top_k_by_default(monkeypatch):
    class RecordingRetrievalService:
        def __init__(self):
            self.calls = []

        def search(self, query: str, top_k: int = 20):
            self.calls.append((query, top_k))
            return [
                RetrievedSource(
                    source_id="chunk-1",
                    document_id="doc-architecture",
                    paper_id="doc-architecture",
                    chunk_id="chunk-1",
                    title="Architecture",
                    section="validation",
                    content="The system validates source ids against retrieved sources.",
                )
            ]

    retrieval = RecordingRetrievalService()
    use_case = RunQueryUseCase(
        retrieval_service=retrieval,
        llm_client=FakeJsonClient(
            {
                "answer_text": "Grounded answer.",
                "cited_source_ids": ["chunk-1"],
            }
        ),
    )

    monkeypatch.setattr("app.use_cases.run_query.get_settings", lambda: type("SettingsStub", (), {"pipeline": type("PipelineStub", (), {"top_k_recall": 11, "temperature_chapter": 0.2})()})())
    result = use_case.execute("What changed in the architecture?")

    assert retrieval.calls == [("What changed in the architecture?", 11)]
    assert result.validation.ok is True
