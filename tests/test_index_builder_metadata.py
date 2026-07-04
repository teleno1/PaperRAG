from pathlib import Path

import numpy as np

from app.domain.models.chunk import Chunk
from app.infrastructure.retrieval.faiss_recall_service import FaissRecallService
from app.infrastructure.vectorstore.faiss_repository import FaissRepository
from app.infrastructure.vectorstore.index_builder import IndexBuilder


class StubChunkBuilder:
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def build_chunks(self, _: Path) -> list[Chunk]:
        return list(self._chunks)


class StubEmbeddingClient:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(index)] for index, _ in enumerate(texts, start=1)]


class StubQueryEmbeddingClient:
    def embed_query(self, _: str):
        return np.array([[1.0]], dtype="float32")


class StubRerankClient:
    def rerank(self, _: str, docs: list[str]) -> list[dict]:
        return [{"index": index, "relevance_score": float(len(docs) - index)} for index, _ in enumerate(docs)]


def test_chunk_to_metadata_includes_document_fields() -> None:
    chunk = Chunk(
        content="Chunk body",
        section="Intro",
        title="PaperRAG",
        authors=["Alice"],
        year="2024",
        venue="ICLR",
    )

    metadata = IndexBuilder._chunk_to_metadata(
        chunk,
        paper_id="paper-001",
        chunk_index=2,
        source_path="data/processed_papers/paper-001/content_list_v2.json",
    )

    assert metadata == {
        "content": "Chunk body",
        "section": "Intro",
        "title": "PaperRAG",
        "authors": ["Alice"],
        "year": "2024",
        "venue": "ICLR",
        "document_id": "paper-001",
        "source_path": "data/processed_papers/paper-001/content_list_v2.json",
        "source_type": "pdf",
        "source_dir": "paper-001",
        "paper_id": "paper-001",
        "chunk_id": "paper-001__chunk_0002",
    }


def test_build_emits_document_metadata_records(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    paper_dir = processed_dir / "paper-001"
    paper_dir.mkdir(parents=True)
    json_path = paper_dir / "content_list_v2.json"
    json_path.write_text("[]", encoding="utf-8")

    chunk = Chunk(
        content="Chunk body",
        section="Methods",
        title="PaperRAG",
        authors=["Alice", "Bob"],
        year="2024",
        venue="ICLR",
    )
    builder = IndexBuilder(
        chunk_builder=StubChunkBuilder([chunk]),
        embedding_client=StubEmbeddingClient(),
    )

    embeddings, metadata = builder.build(processed_dir)

    assert embeddings == [[1.0]]
    assert metadata == [
        {
            "content": "Chunk body",
            "section": "Methods",
            "title": "PaperRAG",
            "authors": ["Alice", "Bob"],
            "year": "2024",
            "venue": "ICLR",
            "document_id": "paper-001",
            "source_path": str(json_path),
            "source_type": "pdf",
            "source_dir": "paper-001",
            "paper_id": "paper-001",
            "chunk_id": "paper-001__chunk_0000",
        }
    ]


def test_saved_metadata_records_round_trip_through_retrieval(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    paper_dir = processed_dir / "paper-001"
    paper_dir.mkdir(parents=True)
    json_path = paper_dir / "content_list_v2.json"
    json_path.write_text("[]", encoding="utf-8")

    builder = IndexBuilder(
        chunk_builder=StubChunkBuilder(
            [
                Chunk(
                    content="Chunk body",
                    section="Methods",
                    title="PaperRAG",
                    authors=["Alice", "Bob"],
                    year="2024",
                    venue="ICLR",
                )
            ]
        ),
        embedding_client=StubEmbeddingClient(),
    )
    vectors, metadata = builder.build(processed_dir)

    repository = FaissRepository(
        index_path=tmp_path / "database" / "paper_index.faiss",
        metadata_path=tmp_path / "database" / "metadata.json",
        embed_dim=1,
    )
    repository.save(vectors, metadata)

    retrieval = FaissRecallService(
        repository=repository,
        embedding_client=StubQueryEmbeddingClient(),
        rerank_client=StubRerankClient(),
    )

    results = retrieval.search("methods", top_k=1)

    assert repository.metadata == metadata
    assert repository.metadata[0]["document_id"] == "paper-001"
    assert repository.metadata[0]["source_path"] == str(json_path)
    assert repository.metadata[0]["source_type"] == "pdf"
    assert len(results) == 1
    assert results[0].paper_id == "paper-001"
    assert results[0].chunk_id == "paper-001__chunk_0000"
    assert results[0].section == "Methods"
