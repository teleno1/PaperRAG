from app.domain.models.adapters import (
    chunk_to_document_chunk,
    paper_metadata_to_document_metadata,
    paper_metadata_to_source,
)
from app.domain.models.chunk import Chunk
from app.domain.models.paper_metadata import PaperMetadata


def test_paper_metadata_to_document_metadata_preserves_legacy_fields() -> None:
    paper_metadata = PaperMetadata(
        title="PaperRAG",
        authors=["Alice", "Bob"],
        year="2024",
        venue="ICLR",
    )

    document_metadata = paper_metadata_to_document_metadata(
        paper_metadata,
        document_id="paper-001",
        paper_id="paper-001",
        source_path="data/processed_papers/paper-001/content_list_v2.json",
        section="Introduction",
        extra_metadata={"language": "en"},
    )

    assert document_metadata.document_id == "paper-001"
    assert document_metadata.source_path == "data/processed_papers/paper-001/content_list_v2.json"
    assert document_metadata.source_type == "pdf"
    assert document_metadata.section == "Introduction"
    assert document_metadata.metadata == {
        "title": "PaperRAG",
        "authors": ["Alice", "Bob"],
        "year": "2024",
        "venue": "ICLR",
        "paper_id": "paper-001",
        "language": "en",
    }


def test_paper_metadata_to_document_metadata_reserves_legacy_keys() -> None:
    paper_metadata = PaperMetadata(title="PaperRAG", authors=["Alice"], year="2024", venue="ICLR")

    document_metadata = paper_metadata_to_document_metadata(
        paper_metadata,
        paper_id="paper-001",
        source_path="data/processed_papers/paper-001/content_list_v2.json",
        extra_metadata={"paper_id": "override", "title": "override", "custom": "value"},
    )

    assert document_metadata.metadata["paper_id"] == "paper-001"
    assert document_metadata.metadata["title"] == "PaperRAG"
    assert document_metadata.metadata["custom"] == "value"


def test_paper_metadata_to_source_uses_document_id_when_source_id_missing() -> None:
    paper_metadata = PaperMetadata(title="PaperRAG", authors=["Alice"], year="2024", venue="ICLR")

    source = paper_metadata_to_source(
        paper_metadata,
        document_id="paper-001",
        source_path="data/processed_papers/paper-001/content_list_v2.json",
    )

    assert source.source_id == "paper-001"
    assert source.metadata["paper_id"] == "paper-001"
    assert source.metadata["title"] == "PaperRAG"


def test_chunk_to_document_chunk_preserves_legacy_metadata_and_ids() -> None:
    chunk = Chunk(
        content="[Title: PaperRAG]\n[Section: Methods]\nA legacy chunk body.",
        section="Methods",
        title="PaperRAG",
        authors=["Alice", "Bob"],
        year="2024",
        venue="ICLR",
    )

    document_chunk = chunk_to_document_chunk(
        chunk,
        paper_id="paper-001",
        chunk_id="paper-001__chunk_0001",
        source_path="data/processed_papers/paper-001/content_list_v2.json",
        extra_metadata={"origin": "mineru"},
    )

    assert document_chunk.chunk_id == "paper-001__chunk_0001"
    assert document_chunk.document_id == "paper-001"
    assert document_chunk.source_type == "pdf"
    assert document_chunk.section == "Methods"
    assert document_chunk.content.endswith("A legacy chunk body.")
    assert document_chunk.metadata == {
        "title": "PaperRAG",
        "authors": ["Alice", "Bob"],
        "year": "2024",
        "venue": "ICLR",
        "paper_id": "paper-001",
        "origin": "mineru",
    }


def test_chunk_to_document_chunk_requires_chunk_id_or_index() -> None:
    chunk = Chunk(content="chunk text", section="Intro", title="PaperRAG")

    try:
        chunk_to_document_chunk(
            chunk,
            document_id="paper-001",
            source_path="data/processed_papers/paper-001/content_list_v2.json",
        )
    except ValueError as exc:
        assert str(exc) == "chunk_id or chunk_index is required"
    else:
        raise AssertionError("expected ValueError when neither chunk_id nor chunk_index is provided")


def test_chunk_to_document_chunk_uses_chunk_index_for_unique_default_ids() -> None:
    chunk = Chunk(content="chunk text", section="Intro", title="PaperRAG")

    first = chunk_to_document_chunk(
        chunk,
        document_id="paper-001",
        chunk_index=0,
        source_path="data/processed_papers/paper-001/content_list_v2.json",
    )
    second = chunk_to_document_chunk(
        chunk,
        document_id="paper-001",
        chunk_index=1,
        source_path="data/processed_papers/paper-001/content_list_v2.json",
    )

    assert first.chunk_id == "paper-001__chunk_0000"
    assert second.chunk_id == "paper-001__chunk_0001"
    assert first.chunk_id != second.chunk_id
