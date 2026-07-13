from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routes import workspaces as workspace_route
from app.domain.models import ParsedDocument, ParsedDocumentUnit
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
            units=[ParsedDocumentUnit(content="A paper paragraph.", section="Findings")],
        )


def test_production_app_delivers_spa_and_keeps_api_404s_json() -> None:
    client = TestClient(app)

    index = client.get("/")
    assert index.status_code == 200
    assert "PaperRAG" in index.text
    assert "/assets/" in index.text

    client_route = client.get("/workspace/example")
    assert client_route.status_code == 200
    assert client_route.text == index.text

    missing_api = client.get("/api/does-not-exist")
    assert missing_api.status_code == 404
    assert missing_api.headers["content-type"].startswith("application/json")


def test_workspace_browser_state_can_rehydrate_persisted_operation_history(tmp_path: Path, monkeypatch) -> None:
    service = ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
    )
    monkeypatch.setattr(workspace_route, "get_workspace_service", lambda: service)
    client = TestClient(app)

    workspace = client.post(
        "/api/workspaces",
        json={"topic": "Evidence attribution", "report_language": "zh"},
    ).json()
    workspace_id = workspace["id"]
    uploaded = client.post(
        f"/api/workspaces/{workspace_id}/papers/upload",
        files={"file": ("paper.pdf", b"%PDF-authorised", "application/pdf")},
    )
    operation_id = uploaded.json()["operation"]["id"]

    for _ in range(50):
        operation = client.get(f"/api/operations/{operation_id}").json()
        if operation["status"] == "succeeded":
            break
        time.sleep(0.01)

    revisited = client.get(f"/api/workspaces/{workspace_id}")
    assert revisited.status_code == 200
    assert revisited.json()["operations"][0]["id"] == operation_id
    assert revisited.json()["operations"][0]["status"] == "succeeded"
    assert client.get(f"/api/workspaces/{workspace_id}/operations").json()[0]["id"] == operation_id
