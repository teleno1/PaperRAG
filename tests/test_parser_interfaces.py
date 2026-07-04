from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import UnsupportedDocumentTypeError
from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.infrastructure.parsing import ParserRegistry


class FakeParser:
    def __init__(self, source_type: str, supported_extensions: tuple[str, ...], section_label: str) -> None:
        self.source_type = source_type
        self.supported_extensions = supported_extensions
        self._section_label = section_label

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        return ParsedDocument(
            document_id=document_id or source_path.stem,
            source_path=str(source_path),
            source_type=self.source_type,
            units=[
                ParsedDocumentUnit(
                    content=f"normalized content for {source_path.name}",
                    section=self._section_label,
                    page_number=1 if self.source_type == "pdf" else None,
                    metadata={"extension": source_path.suffix.lower()},
                )
            ],
            metadata={"parser": self.source_type},
        )


def test_parsed_document_round_trips_with_normalized_units() -> None:
    document = ParsedDocument(
        document_id="doc-123",
        source_path="fixtures/guide.md",
        source_type="Markdown",
        units=[
            ParsedDocumentUnit(
                content="Overview paragraph.",
                section="Overview",
                metadata={"heading_level": 1},
            ),
            ParsedDocumentUnit(
                content="Appendix paragraph.",
                page_number=2,
                metadata={"kind": "appendix"},
            ),
        ],
        metadata={"language": "en"},
    )

    payload = document.to_dict()

    assert payload == {
        "document_id": "doc-123",
        "source_path": "fixtures/guide.md",
        "source_type": "markdown",
        "units": [
            {
                "content": "Overview paragraph.",
                "section": "Overview",
                "page_number": None,
                "metadata": {"heading_level": 1},
            },
            {
                "content": "Appendix paragraph.",
                "section": None,
                "page_number": 2,
                "metadata": {"kind": "appendix"},
            },
        ],
        "metadata": {"language": "en"},
    }
    assert ParsedDocument.from_dict(payload) == document


def test_parser_registry_selects_matching_parser_and_delegates_parse() -> None:
    registry = ParserRegistry(
        parsers=[
            FakeParser(source_type="pdf", supported_extensions=(".pdf",), section_label="Page 1"),
            FakeParser(source_type="txt", supported_extensions=(".txt",), section_label="Body"),
            FakeParser(source_type="markdown", supported_extensions=(".md", ".markdown"), section_label="Heading"),
        ]
    )

    parsed = registry.parse(Path("fixtures/Guide.MD"), document_id="guide-doc")

    assert parsed.document_id == "guide-doc"
    assert parsed.source_type == "markdown"
    assert parsed.units[0].content == "normalized content for Guide.MD"
    assert parsed.units[0].section == "Heading"
    assert registry.supported_extensions() == [".pdf", ".txt", ".md", ".markdown"]


def test_parser_registry_raises_for_unknown_extension() -> None:
    registry = ParserRegistry(
        parsers=[FakeParser(source_type="txt", supported_extensions=(".txt",), section_label="Body")]
    )

    with pytest.raises(UnsupportedDocumentTypeError) as exc_info:
        registry.select_parser(Path("fixtures/notes.rst"))

    error = exc_info.value
    assert Path(error.source_path) == Path("fixtures/notes.rst")
    assert error.supported_extensions == [".txt"]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "document_id": "doc-1",
                "source_path": "notes.txt",
                "source_type": "txt",
                "units": "not-a-list",
            },
            "units must be a list",
        ),
        (
            {
                "document_id": "doc-1",
                "source_path": "notes.txt",
                "source_type": "txt",
                "units": [123],
            },
            "units must contain dict items",
        ),
        (
            {
                "content": "Page body",
                "section": "  ",
            },
            "section must not be empty",
        ),
        (
            {
                "content": "Page body",
                "page_number": 0,
            },
            "page_number must be greater than or equal to 1",
        ),
        (
            {
                "content": "Page body",
                "page_number": True,
            },
            "page_number must be an int",
        ),
    ],
)
def test_parsed_document_models_reject_invalid_payloads(payload, message) -> None:
    if "document_id" in payload:
        factory = ParsedDocument.from_dict
    else:
        factory = ParsedDocumentUnit.from_dict

    with pytest.raises(ValueError, match=message):
        factory(payload)
