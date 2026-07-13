from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app
from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.domain.workspace import DiscoveryCandidate, DiscoveryPage
from app.infrastructure.discovery import PaperDiscoveryProvider, PdfDownloader
from app.infrastructure.parsing import ParserRegistry
from app.infrastructure.workspace.repository import WorkspaceRepository
from app.use_cases.workspace import ResearchWorkspaceService


class FakePdfParser:
    source_type = "pdf"
    supported_extensions = (".pdf",)

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        return ParsedDocument(
            document_id=document_id or "document-version",
            source_path=str(source_path),
            source_type="pdf",
            units=[ParsedDocumentUnit(content="A paper paragraph.", section="Findings", page_number=2)],
        )


class FakeProvider(PaperDiscoveryProvider):
    name = "openalex"

    def search(self, query: str, *, page: int = 1, per_page: int = 10) -> DiscoveryPage:
        return DiscoveryPage(
            provider=self.name,
            query=query,
            candidates=[
                DiscoveryCandidate(
                    provider=self.name,
                    provider_id="W123",
                    title="Open Candidate",
                    authors=["Grace Hopper"],
                    abstract="Candidate abstract",
                    year="2025",
                    venue="Open Venue",
                    doi="10.5555/open",
                    source_url="https://example.test/open",
                    pdf_url="https://example.test/open.pdf",
                    is_open_access=True,
                )
            ],
            page=page,
            per_page=per_page,
            total_count=1,
        )


class FakeDownloader(PdfDownloader):
    def download(self, url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"%PDF-api")


def test_workspace_discovery_api_returns_candidate_then_polls_import(tmp_path: Path, monkeypatch) -> None:
    from app.api.routes import workspaces as workspace_route

    service = ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
        discovery_providers={"openalex": FakeProvider()},
        pdf_downloader=FakeDownloader(),
    )
    monkeypatch.setattr(workspace_route, "get_workspace_service", lambda: service)
    client = TestClient(app)

    workspace = client.post(
        "/api/workspaces",
        json={"topic": "Evidence attribution", "report_language": "en"},
    ).json()
    discovered = client.post(
        f"/api/workspaces/{workspace['id']}/papers/discover",
        json={"query": "evidence attribution", "provider": "openalex"},
    )

    assert discovered.status_code == 200
    candidate = discovered.json()["candidates"][0]
    assert candidate["selected"] is False
    assert candidate["evidence_eligible"] is False
    assert candidate["authors"] == ["Grace Hopper"]
    assert candidate["source_url"] == "https://example.test/open"
    assert "storage_path" not in candidate
    assert "provider" not in candidate
    assert "provider_id" not in candidate
    assert "provider" not in discovered.json()

    imported = client.post(
        f"/api/workspaces/{workspace['id']}/papers/{candidate['id']}/import",
    )
    assert imported.status_code == 202
    operation_id = imported.json()["operation"]["id"]
    operation = client.get(f"/api/operations/{operation_id}")
    for _ in range(50):
        if operation.json()["status"] == "succeeded":
            break
        time.sleep(0.01)
        operation = client.get(f"/api/operations/{operation_id}")
    assert operation.json()["status"] == "succeeded"
    assert client.get(f"/api/workspaces/{workspace['id']}").json()["papers"][0]["evidence_eligible"] is True

    authorised = client.post(
        f"/api/workspaces/{workspace['id']}/papers/upload",
        data={"candidate_id": candidate["id"]},
        files={"file": ("authorised-copy.pdf", b"%PDF-authorised", "application/pdf")},
    )
    assert authorised.status_code == 202
    assert authorised.json()["paper"]["id"] == candidate["id"]
    assert authorised.json()["paper"]["source_kind"] == "discovery"
