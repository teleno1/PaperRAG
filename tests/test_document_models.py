import pytest

from app.domain.models.document import DocumentChunk, DocumentMetadata, Source


def test_source_normalizes_and_serializes_metadata() -> None:
    source = Source(
        source_id=" doc-source ",
        source_path=" docs/spec.md ",
        source_type="Markdown",
        metadata={"owner": "tests"},
    )

    assert source.source_id == "doc-source"
    assert source.source_path == "docs/spec.md"
    assert source.source_type == "markdown"
    assert source.to_dict() == {
        "source_id": "doc-source",
        "source_path": "docs/spec.md",
        "source_type": "markdown",
        "metadata": {"owner": "tests"},
    }


def test_document_metadata_rejects_blank_required_fields() -> None:
    with pytest.raises(ValueError, match="document_id must not be empty"):
        DocumentMetadata(document_id=" ", source_path="doc.md", source_type="markdown")


def test_document_metadata_round_trips_through_dict() -> None:
    metadata = DocumentMetadata(
        document_id="doc-123",
        source_path="notes/doc.md",
        source_type="Markdown",
        section="Overview",
        metadata={"topic": "rag"},
    )

    payload = metadata.to_dict()

    assert payload == {
        "document_id": "doc-123",
        "source_path": "notes/doc.md",
        "source_type": "markdown",
        "section": "Overview",
        "metadata": {"topic": "rag"},
    }
    assert DocumentMetadata.from_dict(payload) == metadata


def test_document_chunk_round_trips_through_dict() -> None:
    chunk = DocumentChunk(
        chunk_id="chunk-001",
        document_id="doc-123",
        source_path="notes/doc.md",
        source_type="Markdown",
        section="Overview",
        content="A concise chunk of text.",
        metadata={"page": 1, "score": 0.9},
    )

    payload = chunk.to_dict()

    assert payload == {
        "chunk_id": "chunk-001",
        "document_id": "doc-123",
        "source_path": "notes/doc.md",
        "source_type": "markdown",
        "section": "Overview",
        "content": "A concise chunk of text.",
        "metadata": {"page": 1, "score": 0.9},
    }
    assert DocumentChunk.from_dict(payload) == chunk


@pytest.mark.parametrize(
    ("factory", "payload", "message"),
    [
        (Source.from_dict, {"source_id": None, "source_path": "doc.md", "source_type": "markdown"}, "source_id must be a string"),
        (
            DocumentMetadata.from_dict,
            {"document_id": None, "source_path": "doc.md", "source_type": "markdown", "section": "Intro"},
            "document_id must be a string",
        ),
        (
            DocumentChunk.from_dict,
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "source_path": "doc.md",
                "source_type": "markdown",
                "section": "Intro",
                "content": None,
            },
            "content must be a string",
        ),
    ],
)
def test_from_dict_rejects_non_string_required_fields(factory, payload, message) -> None:
    with pytest.raises(ValueError, match=message):
        factory(payload)
