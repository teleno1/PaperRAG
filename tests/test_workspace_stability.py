from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routes import workspaces as workspace_route
from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.domain.workspace import DiscoveryCandidate, DiscoveryPage
from app.infrastructure.discovery import PaperDiscoveryProvider, PdfDownloadError, PdfDownloader
from app.infrastructure.parsing import ParserRegistry
from app.infrastructure.workspace.repository import SCHEMA, WorkspaceRepository
from app.use_cases.workspace import ResearchWorkspaceService


class FakeParser:
    source_type = "pdf"
    supported_extensions = (".pdf",)

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        return ParsedDocument(
            document_id=document_id or "document-version",
            source_path=str(source_path),
            source_type="pdf",
            units=[ParsedDocumentUnit(content="Evidence paragraph.", section="Findings", page_number=1)],
        )


class FakeProvider(PaperDiscoveryProvider):
    name = "openalex"

    def __init__(self, pdf_urls: list[str] | None = None) -> None:
        self.calls = 0
        self.pdf_urls = pdf_urls or []

    def search(self, query: str, *, page: int = 1, per_page: int = 10) -> DiscoveryPage:
        self.calls += 1
        return DiscoveryPage(
            provider=self.name,
            query=query,
            candidates=[
                DiscoveryCandidate(
                    provider=self.name,
                    provider_id="W-stability",
                    title="Stability candidate",
                    source_url="https://example.test/paper",
                    pdf_url=self.pdf_urls[0] if self.pdf_urls else None,
                    pdf_urls=self.pdf_urls,
                    is_open_access=True if self.pdf_urls else None,
                )
            ],
            page=page,
            per_page=per_page,
            total_count=1,
        )


class FakeDownloader(PdfDownloader):
    def __init__(self, failing_urls: set[str] | None = None) -> None:
        self.failing_urls = failing_urls or set()
        self.calls: list[str] = []

    def download(self, url: str, destination: Path) -> None:
        self.calls.append(url)
        if url in self.failing_urls:
            raise PdfDownloadError("not_a_pdf", "The selected public URL did not return a PDF.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"%PDF-stability")


def build_service(
    tmp_path: Path,
    provider: FakeProvider | None = None,
    downloader: FakeDownloader | None = None,
) -> ResearchWorkspaceService:
    return ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakeParser()]),
        storage_root=tmp_path / "workspace-files",
        discovery_providers={"openalex": provider or FakeProvider()},
        pdf_downloader=downloader or FakeDownloader(),
    )


def test_candidate_can_be_dismissed_and_restored_without_deleting_history(tmp_path: Path) -> None:
    provider = FakeProvider()
    service = build_service(tmp_path, provider)
    workspace = service.create_workspace(topic="Evidence", report_language="zh")
    candidate = service.discover_papers(workspace.id, provider="openalex").candidates[0]

    dismissed = service.dismiss_paper(workspace.id, candidate.id)
    assert dismissed.dismissed is True
    assert service.discover_papers(workspace.id, provider="openalex").candidates == []
    assert service.get_workspace(workspace.id).papers[0].id == candidate.id

    restored = service.restore_dismissed_paper(workspace.id, candidate.id)
    assert restored.dismissed is False
    assert len(service.discover_papers(workspace.id, provider="openalex").candidates) == 1


def test_import_tries_multiple_public_pdf_locations_in_order(tmp_path: Path) -> None:
    provider = FakeProvider(["https://example.test/first", "https://example.test/second"])
    downloader = FakeDownloader({"https://example.test/first"})
    service = build_service(tmp_path, provider, downloader)
    workspace = service.create_workspace(topic="Evidence", report_language="zh")
    candidate = service.discover_papers(workspace.id, provider="openalex").candidates[0]

    result = service.import_discovered_paper(workspace.id, candidate.id)

    assert downloader.calls == ["https://example.test/first", "https://example.test/second"]
    assert result.paper.evidence_readiness == "ready"


def test_candidate_dismiss_and_restore_api_are_workspace_scoped(tmp_path: Path, monkeypatch) -> None:
    service = build_service(tmp_path)
    monkeypatch.setattr(workspace_route, "get_workspace_service", lambda: service)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"topic": "Evidence", "report_language": "zh"}).json()["id"]
    candidate = client.post(
        f"/api/workspaces/{workspace_id}/papers/discover",
        json={"query": "evidence", "provider": "openalex"},
    ).json()["candidates"][0]

    dismissed = client.post(f"/api/workspaces/{workspace_id}/papers/{candidate['id']}/dismiss")
    assert dismissed.status_code == 200
    assert dismissed.json()["dismissed"] is True
    repeated = client.post(
        f"/api/workspaces/{workspace_id}/papers/discover",
        json={"query": "evidence", "provider": "openalex"},
    )
    assert repeated.json()["candidates"] == []

    restored = client.post(f"/api/workspaces/{workspace_id}/papers/{candidate['id']}/restore")
    assert restored.status_code == 200
    assert restored.json()["dismissed"] is False


def test_old_workspace_database_gains_dismissal_columns_without_data_loss(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    legacy_schema = SCHEMA.replace("    pdf_urls_json TEXT NOT NULL DEFAULT '[]',\n", "")
    legacy_schema = legacy_schema.replace("    dismissed_at TEXT,\n", "")
    legacy_schema = legacy_schema.replace("CREATE INDEX IF NOT EXISTS idx_papers_dismissed ON papers(workspace_id, dismissed_at);\n", "")
    with sqlite3.connect(database_path) as connection:
        connection.executescript(legacy_schema)
        connection.execute(
            "INSERT INTO workspaces (id, topic, report_language, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("legacy-workspace", "Evidence", "zh", "setup", "2026-07-13T00:00:00Z", "2026-07-13T00:00:00Z"),
        )
        connection.execute(
            """
            INSERT INTO papers (
                id, workspace_id, title, source_kind, original_filename, storage_path,
                selected, evidence_readiness, active_document_version_id, authors_json,
                year, venue, failure_phase, failure_message, retryable,
                provider, provider_id, doi, arxiv_id, abstract, source_url, pdf_url,
                is_open_access, license, source_links_json, discovery_query, discovered_at,
                published_at, source_updated_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-paper",
                "legacy-workspace",
                "Legacy paper",
                "discovery",
                "legacy.pdf",
                "",
                0,
                "unavailable",
                None,
                '["Author"]',
                "2024",
                "Venue",
                None,
                None,
                0,
                "openalex",
                "W-legacy",
                None,
                None,
                "Legacy abstract",
                "https://example.test/legacy",
                "https://example.test/legacy.pdf",
                1,
                "cc-by",
                '["https://example.test/legacy"]',
                "evidence",
                "2026-07-13T00:00:00Z",
                "2024-01-01",
                "2024-01-02",
                "2026-07-13T00:00:00Z",
                "2026-07-13T00:00:00Z",
            ),
        )

    repository = WorkspaceRepository(database_path)
    columns = {
        row[1]
        for row in sqlite3.connect(database_path).execute("PRAGMA table_info(papers)").fetchall()
    }

    assert {"pdf_urls_json", "dismissed_at"}.issubset(columns)
    restored = repository.get_workspace("legacy-workspace")
    assert restored is not None
    assert restored.papers[0].id == "legacy-paper"
    assert restored.papers[0].pdf_urls == ["https://example.test/legacy.pdf"]
    assert restored.papers[0].dismissed is False


def test_outline_history_restore_creates_new_draft_and_preserves_source(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    workspace = service.create_workspace(topic="Evidence", report_language="zh")
    upload = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-paper")
    first = service.generate_outline(workspace.id)
    approved = service.approve_outline(workspace.id, revision_id=first.id)
    restored = service.restore_outline_revision(workspace.id, approved.id)

    assert restored.id != approved.id
    assert restored.revision_number == approved.revision_number + 1
    assert restored.status == "draft"
    assert restored.title == approved.title
    assert restored.research_question == approved.research_question
    assert restored.sections == approved.sections
    assert restored.evidence_paper_ids == [upload.paper.id]
    history = service.list_outline_revisions(workspace.id)
    assert history[1].id == approved.id
    assert history[1].status == "approved"


def test_outline_history_restore_api_returns_new_draft(tmp_path: Path, monkeypatch) -> None:
    service = build_service(tmp_path)
    monkeypatch.setattr(workspace_route, "get_workspace_service", lambda: service)
    client = TestClient(app)
    workspace_id = client.post("/api/workspaces", json={"topic": "Evidence", "report_language": "zh"}).json()["id"]
    service.upload_paper(workspace_id, filename="paper.pdf", content=b"%PDF-paper")
    outline = service.generate_outline(workspace_id)
    approved = service.approve_outline(workspace_id, revision_id=outline.id)

    restored = client.post(f"/api/workspaces/{workspace_id}/outline/revisions/{approved.id}/restore")
    assert restored.status_code == 200
    assert restored.json()["status"] == "draft"
    assert restored.json()["id"] != approved.id
