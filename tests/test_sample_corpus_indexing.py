from __future__ import annotations

from pathlib import Path

from app.infrastructure.parsing import MarkdownParser, ParserRegistry, TxtParser
from app.infrastructure.vectorstore.faiss_repository import FaissRepository
from app.infrastructure.vectorstore.index_builder import IndexBuilder

SAMPLE_CORPUS_DIR = Path(__file__).resolve().parent.parent / "data" / "samples" / "phase2_corpus"


class FakeEmbeddingClient:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(index + 1), float(len(text) % 17)] for index, text in enumerate(texts)]


def test_sample_txt_and_markdown_corpus_can_be_indexed_without_mineru(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("MINERU_API_KEY", raising=False)

    index_builder = IndexBuilder(
        embedding_client=FakeEmbeddingClient(),
        parser_registry=ParserRegistry(parsers=[TxtParser(), MarkdownParser()]),
    )

    vectors, metadata = index_builder.build_from_source_dir(SAMPLE_CORPUS_DIR)

    repository = FaissRepository(
        index_path=tmp_path / "sample_index.faiss",
        metadata_path=tmp_path / "metadata.json",
        embed_dim=2,
    )
    repository.save(vectors=vectors, metadata=metadata)

    assert repository.exists()
    assert repository.count() == len(metadata)
    assert repository.count() >= 2
    assert {item["document_id"] for item in metadata} == {"product_notes", "retrieval_playbook"}
    assert {item["source_type"] for item in metadata} == {"txt", "markdown"}
    assert all(item["chunk_id"].startswith(f"{item['document_id']}__chunk_") for item in metadata)
    assert all(Path(item["source_path"]).is_relative_to(SAMPLE_CORPUS_DIR) for item in metadata)
    assert any(item["section"] != "UNKNOWN" for item in metadata)


def test_default_index_builder_registry_skips_mineru_for_non_pdf_corpus(monkeypatch) -> None:
    monkeypatch.delenv("MINERU_API_KEY", raising=False)

    vectors, metadata = IndexBuilder(embedding_client=FakeEmbeddingClient()).build_from_source_dir(SAMPLE_CORPUS_DIR)

    assert len(vectors) == len(metadata)
    assert {item["source_type"] for item in metadata} == {"txt", "markdown"}
