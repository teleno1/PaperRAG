from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app
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
            units=[ParsedDocumentUnit(content="A paper paragraph.")],
        )


def test_workspace_api_supports_create_upload_revisit_and_operation_polling(tmp_path: Path, monkeypatch) -> None:
    from app.api.routes import workspaces as workspace_route

    service = ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
    )
    monkeypatch.setattr(workspace_route, "get_workspace_service", lambda: service)
    client = TestClient(app)

    created = client.post(
        "/api/workspaces",
        json={"topic": "Evidence attribution", "report_language": "en"},
    )
    assert created.status_code == 201
    workspace_id = created.json()["id"]

    uploaded = client.post(
        f"/api/workspaces/{workspace_id}/papers/upload",
        files={"file": ("paper.pdf", b"%PDF-authorised", "application/pdf")},
    )
    assert uploaded.status_code == 202
    payload = uploaded.json()
    assert payload["paper"]["selected"] is True
    assert payload["paper"]["evidence_readiness"] == "importing"
    assert payload["operation"]["status"] == "queued"

    revisited = client.get(f"/api/workspaces/{workspace_id}")
    assert revisited.status_code == 200
    assert revisited.json()["papers"][0]["title"] == "paper"

    operation_id = payload["operation"]["id"]
    operation = client.get(f"/api/operations/{operation_id}")
    for _ in range(50):
        if operation.json().get("status") == "succeeded":
            break
        time.sleep(0.01)
        operation = client.get(f"/api/operations/{operation_id}")
    assert operation.status_code == 200
    assert operation.json()["workspace_id"] == workspace_id
    assert operation.json()["status"] == "succeeded"


def test_workspace_api_rejects_non_pdf_upload(tmp_path: Path, monkeypatch) -> None:
    from app.api.routes import workspaces as workspace_route

    service = ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
    )
    monkeypatch.setattr(workspace_route, "get_workspace_service", lambda: service)
    client = TestClient(app)
    workspace_id = client.post(
        "/api/workspaces",
        json={"topic": "Evidence attribution", "report_language": "zh"},
    ).json()["id"]

    response = client.post(
        f"/api/workspaces/{workspace_id}/papers/upload",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_upload"
