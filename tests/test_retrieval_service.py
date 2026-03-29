import importlib

import numpy as np

from app.infrastructure.llm.clients import DeepSeekJsonClient
from app.infrastructure.retrieval.faiss_recall_service import FaissRecallService


def test_retrieval_module_import_has_no_side_effect():
    module = importlib.import_module("app.infrastructure.retrieval.faiss_recall_service")
    assert hasattr(module, "FaissRecallService")


class FakeRepository:
    def exists(self):
        return True

    def count(self):
        return 2

    def search(self, query_vector, top_k):
        return np.array([[0.1, 0.2]]), np.array([[0, 1]])

    @property
    def metadata(self):
        return [
            {
                "paper_id": "paper-1",
                "chunk_id": "chunk-1",
                "title": "Paper 1",
                "authors": ["A"],
                "year": "2024",
                "venue": "Venue",
                "section": "Introduction",
                "content": "Chunk 1",
            },
            {
                "paper_id": "paper-2",
                "chunk_id": "chunk-2",
                "title": "Paper 2",
                "authors": ["B"],
                "year": "2023",
                "venue": "Venue",
                "section": "Method",
                "content": "Chunk 2",
            },
        ]


class FakeEmbeddingClient:
    def embed_query(self, query: str):
        return np.zeros((1, 2), dtype="float32")


class FakeRerankClient:
    def rerank(self, query: str, docs):
        return [{"index": idx, "relevance_score": float(len(docs) - idx)} for idx in range(len(docs))]


def test_retrieval_search_returns_models():
    service = FaissRecallService(
        repository=FakeRepository(),
        embedding_client=FakeEmbeddingClient(),
        rerank_client=FakeRerankClient(),
    )
    results = service.search("query", top_k=2)
    assert len(results) == 2
    assert results[0].paper_id
    assert results[0].chunk_id


def test_deepseek_json_client_parses_fenced_or_wrapped_json():
    assert DeepSeekJsonClient._parse_json_content('{"a": 1}') == {"a": 1}
    assert DeepSeekJsonClient._parse_json_content("```json\n{\"a\": 1}\n```") == {"a": 1}
    assert DeepSeekJsonClient._parse_json_content("下面是结果：\n```json\n[\"x\", \"y\"]\n```") == ["x", "y"]
