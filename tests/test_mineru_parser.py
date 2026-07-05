from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings
from app.core.paths import PathManager
from app.infrastructure.parsing import MarkdownParser, MinerUParser, ParserRegistry


class FakeMinerUClient:
    def __init__(self, manifest_name: str = "content_list_v2.json") -> None:
        self.manifest_name = manifest_name
        self.output_dirs: list[Path] = []

    def parse_pdf(self, pdf_path: Path, output_dir: Path) -> Path:
        self.output_dirs.append(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = [
            [
                {
                    "type": "title",
                    "content": {
                        "title_content": [
                            {"type": "text", "content": "Overview"},
                        ]
                    },
                },
                {
                    "type": "paragraph",
                    "content": {
                        "paragraph_content": [
                            {"type": "text", "content": "First paragraph."},
                            {"type": "text", "content": "Second paragraph."},
                        ]
                    },
                },
            ],
            [
                {
                    "type": "list",
                    "content": {
                        "list_type": "text_list",
                        "list_items": [
                            {
                                "item_content": [
                                    {"type": "text", "content": "Bullet item"},
                                ]
                            }
                        ],
                    },
                }
            ],
        ]
        (output_dir / self.manifest_name).write_text(json.dumps(payload), encoding="utf-8")
        return output_dir


def _paths(tmp_path: Path) -> PathManager:
    settings = get_settings().model_copy(deep=True)
    settings.paths.processed_dir = str(tmp_path / "processed")
    return PathManager(settings_override=settings)


def test_mineru_parser_converts_pdf_output_to_normalized_units(tmp_path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF")

    parsed = MinerUParser(mineru_client=FakeMinerUClient(), output_root=tmp_path / "processed").parse(pdf_path)

    assert parsed.document_id == "paper"
    assert parsed.source_type == "pdf"
    assert parsed.metadata["parser"] == "mineru"
    assert [unit.section for unit in parsed.units] == ["Overview", "Overview", "Overview"]
    assert [unit.page_number for unit in parsed.units] == [1, 1, 2]
    assert [unit.content for unit in parsed.units] == [
        "First paragraph.",
        "Second paragraph.",
        "- Bullet item",
    ]


def test_mineru_parser_defaults_to_processed_dir_layout(tmp_path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF")
    fake_client = FakeMinerUClient()
    paths = _paths(tmp_path)

    parsed = MinerUParser(mineru_client=fake_client, paths=paths).parse(pdf_path)

    assert fake_client.output_dirs == [paths.processed_dir / "paper"]
    assert Path(parsed.metadata["mineru_output_dir"]) == paths.processed_dir / "paper"


def test_mineru_parser_accepts_prefixed_manifest_name(tmp_path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF")

    parsed = MinerUParser(
        mineru_client=FakeMinerUClient(manifest_name="task-123_content_list_v2.json"),
        output_root=tmp_path / "processed",
    ).parse(pdf_path)

    assert parsed.document_id == "paper"
    assert [unit.content for unit in parsed.units] == [
        "First paragraph.",
        "Second paragraph.",
        "- Bullet item",
    ]


def test_non_pdf_registry_flow_does_not_require_mineru_key(monkeypatch, tmp_path) -> None:
    fixtures_dir = Path(__file__).parent / "fixtures" / "parsing"
    monkeypatch.delenv("MINERU_API_KEY", raising=False)

    parsed = ParserRegistry(
        parsers=[MarkdownParser(), MinerUParser(mineru_client=FakeMinerUClient(), paths=_paths(tmp_path))]
    ).parse(fixtures_dir / "sample.md")

    assert parsed.source_type == "markdown"
    assert len(parsed.units) == 3
