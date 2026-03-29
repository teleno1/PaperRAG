from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.llm.clients import (
    DashScopeEmbeddingClient,
    DashScopeRerankClient,
    MULTIMODAL_EMBEDDING_URL,
    RERANK_URL,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


def test_qwen3_vl_embedding_uses_multimodal_endpoint(monkeypatch):
    captured: dict = {}
    settings = Settings(
        models={
            "embedding_model": "qwen3-vl-embedding",
            "embedding_dimension": 1024,
            "dashscope_api_key": "test-key",
        }
    )

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            200,
            {
                "output": {
                    "embeddings": [
                        {"embedding": [0.1, 0.2]},
                        {"embedding": [0.3, 0.4]},
                    ]
                }
            },
        )

    monkeypatch.setattr("app.infrastructure.llm.clients.requests.post", fake_post)

    client = DashScopeEmbeddingClient(settings=settings)
    result = client.embed_texts(["hello", "world"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert captured["url"] == MULTIMODAL_EMBEDDING_URL
    assert captured["json"] == {
        "model": "qwen3-vl-embedding",
        "input": {"contents": [{"text": "hello"}, {"text": "world"}]},
        "parameters": {"dimension": 1024},
    }


def test_text_embedding_compatible_mode_uses_dimensions_parameter():
    captured: dict = {}
    settings = Settings(
        models={
            "embedding_model": "text-embedding-v4",
            "embedding_dimension": 768,
            "dashscope_api_key": "test-key",
        }
    )

    class FakeEmbeddings:
        def create(self, **kwargs):
            captured.update(kwargs)

            class Item:
                embedding = [0.1, 0.2]

            class Response:
                data = [Item()]

            return Response()

    class FakeClient:
        embeddings = FakeEmbeddings()

    client = DashScopeEmbeddingClient(settings=settings)
    client._client = FakeClient()
    result = client.embed_texts(["hello"])

    assert result == [[0.1, 0.2]]
    assert captured == {
        "model": "text-embedding-v4",
        "input": ["hello"],
        "dimensions": 768,
    }


def test_qwen3_vl_rerank_wraps_query_and_docs_as_text(monkeypatch):
    captured: dict = {}
    settings = Settings(
        models={
            "rerank_model": "qwen3-vl-rerank",
            "dashscope_api_key": "test-key",
        }
    )

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            200,
            {
                "output": {
                    "results": [
                        {"index": 1, "relevance_score": 0.9},
                        {"index": 0, "relevance_score": 0.7},
                    ]
                }
            },
        )

    monkeypatch.setattr("app.infrastructure.llm.clients.requests.post", fake_post)

    client = DashScopeRerankClient(settings=settings)
    result = client.rerank("query text", ["doc 1", "doc 2"])

    assert result == [
        {"index": 1, "relevance_score": 0.9},
        {"index": 0, "relevance_score": 0.7},
    ]
    assert captured["url"] == RERANK_URL
    assert captured["json"] == {
        "model": "qwen3-vl-rerank",
        "input": {
            "query": {"text": "query text"},
            "documents": [{"text": "doc 1"}, {"text": "doc 2"}],
        },
    }


def test_qwen3_vl_embedding_retries_and_splits_batch_on_retryable_error(monkeypatch):
    calls: list[list[str]] = []
    settings = Settings(
        models={
            "embedding_model": "qwen3-vl-embedding",
            "embedding_dimension": 1024,
            "dashscope_api_key": "test-key",
        }
    )

    def fake_post(url, headers=None, json=None, timeout=None):
        texts = [item["text"] for item in json["input"]["contents"]]
        calls.append(texts)
        if len(texts) > 1:
            return FakeResponse(500, {"message": "InternalError.Algo.Embedding_pipeline_Error"})
        return FakeResponse(
            200,
            {"output": {"embeddings": [{"embedding": [float(len(texts[0])), 1.0]}]}},
        )

    monkeypatch.setattr("app.infrastructure.llm.clients.requests.post", fake_post)
    monkeypatch.setattr("app.infrastructure.llm.clients.time.sleep", lambda _: None)

    client = DashScopeEmbeddingClient(settings=settings)
    result = client.embed_texts(["a", "bb"])

    assert result == [[1.0, 1.0], [2.0, 1.0]]
    assert calls[:3] == [["a", "bb"], ["a", "bb"], ["a", "bb"]]
    assert ["a"] in calls
    assert ["bb"] in calls
