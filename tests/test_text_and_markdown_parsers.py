from __future__ import annotations

from pathlib import Path

from app.infrastructure.parsing import MarkdownParser, TxtParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "parsing"


def test_txt_parser_returns_plain_text_as_single_unit(monkeypatch) -> None:
    monkeypatch.delenv("MINERU_API_KEY", raising=False)

    parsed = TxtParser().parse(FIXTURES_DIR / "sample.txt")

    assert parsed.document_id == "sample"
    assert parsed.source_type == "txt"
    assert len(parsed.units) == 1
    assert parsed.units[0].section is None
    assert parsed.units[0].content == (
        "PaperRAG is becoming a general knowledge-base RAG system.\n"
        "This plain text file should be parsed without any API keys."
    )
    assert parsed.units[0].metadata == {"line_count": 2}


def test_markdown_parser_splits_sections_by_heading() -> None:
    parsed = MarkdownParser().parse(FIXTURES_DIR / "sample.md", document_id="kb-doc")

    assert parsed.document_id == "kb-doc"
    assert parsed.source_type == "markdown"
    assert [unit.section for unit in parsed.units] == [None, "Overview", "Details"]
    assert [unit.metadata for unit in parsed.units] == [{}, {"heading_level": 1}, {"heading_level": 2}]
    assert parsed.units[0].content == "Intro text before any heading."
    assert parsed.units[1].content == (
        "PaperRAG now supports Markdown parsing.\n"
        "It should preserve section headings."
    )
    assert parsed.units[2].content == "The parser should emit deterministic normalized units."
