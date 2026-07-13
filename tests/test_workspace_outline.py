from __future__ import annotations

from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routes import workspaces as workspace_route
from app.core.exceptions import OutlineUnavailableError
from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.domain.outline import OutlineSection
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
            units=[ParsedDocumentUnit(content="Evidence paragraph.", section="Findings")],
        )


def build_service(tmp_path: Path) -> ResearchWorkspaceService:
    return ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
    )


def test_outline_generation_requires_ready_selected_evidence(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    workspace = service.create_workspace(topic="Evidence attribution", report_language="zh")

    with pytest.raises(OutlineUnavailableError, match="ready Selected Paper") as error:
        service.generate_outline(workspace.id)

    assert error.value.next_action.startswith("select and process")


def test_outline_revision_can_be_edited_approved_and_reopened_without_rewriting_history(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    workspace = service.create_workspace(topic="Evidence attribution", report_language="zh")
    upload = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")

    draft = service.generate_outline(workspace.id)
    assert draft.status == "draft"
    assert draft.evidence_paper_ids == [upload.paper.id]
    assert [section.title for section in draft.sections] == [
        "研究问题与范围",
        "方法与主要发现",
        "研究比较",
        "局限与研究缺口",
        "结论",
        "参考文献",
    ]

    edited = service.save_outline(
        workspace.id,
        revision_id=draft.id,
        title=draft.title,
        research_question="新的研究问题",
        sections=[draft.sections[1], draft.sections[0]],
    )
    assert edited.id == draft.id
    assert edited.research_question == "新的研究问题"
    approved = service.approve_outline(workspace.id, revision_id=edited.id)
    assert approved.status == "approved"
    assert approved.id == draft.id

    reopened = service.save_outline(
        workspace.id,
        revision_id=approved.id,
        title="编辑后的大纲",
        research_question="批准后重新编辑",
        sections=[OutlineSection("custom", "自定义章节")],
    )
    assert reopened.id != approved.id
    assert reopened.revision_number == approved.revision_number + 1
    assert reopened.status == "draft"
    assert service.list_outline_revisions(workspace.id)[0].id == reopened.id
    assert service.list_outline_revisions(workspace.id)[1].status == "approved"
    assert service.list_outline_revisions(workspace.id)[1].title == draft.title


def test_outline_api_rehydrates_current_revision_and_rejects_empty_evidence(tmp_path: Path, monkeypatch) -> None:
    service = build_service(tmp_path)
    monkeypatch.setattr(workspace_route, "get_workspace_service", lambda: service)
    client = TestClient(app)
    workspace_id = client.post(
        "/api/workspaces",
        json={"topic": "Evidence attribution", "report_language": "en"},
    ).json()["id"]

    unavailable = client.post(f"/api/workspaces/{workspace_id}/outline/generate")
    assert unavailable.status_code == 400
    assert unavailable.json()["error"] == "outline_unavailable"
    assert "select and process" in unavailable.json()["next_action"]

    upload = client.post(
        f"/api/workspaces/{workspace_id}/papers/upload",
        files={"file": ("paper.pdf", b"%PDF-authorised", "application/pdf")},
    )
    assert upload.status_code == 202
    for _ in range(50):
        if client.get(f"/api/operations/{upload.json()['operation']['id']}").json()["status"] == "succeeded":
            break
        time.sleep(0.01)
    outline_start = client.post(f"/api/workspaces/{workspace_id}/outline/generate")
    assert outline_start.status_code == 202
    outline_operation_id = outline_start.json()["id"]
    for _ in range(50):
        if client.get(f"/api/operations/{outline_operation_id}").json()["status"] == "succeeded":
            break
        time.sleep(0.01)
    outline = client.get(f"/api/workspaces/{workspace_id}/outline")
    assert outline.status_code == 200
    outline_payload = outline.json()
    assert outline_payload["status"] == "draft"
    assert len(outline_payload["evidence_paper_ids"]) == 1

    saved = client.put(
        f"/api/workspaces/{workspace_id}/outline",
        json={
            "revision_id": outline_payload["id"],
            "title": outline_payload["title"],
            "research_question": "Edited question",
            "sections": [
                {"id": "research-question", "title": "Research question", "description": "Scope"},
            ],
        },
    )
    assert saved.status_code == 200
    approved = client.post(
        f"/api/workspaces/{workspace_id}/outline/approve",
        json={"revision_id": saved.json()["id"]},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    missing_revision = client.post(f"/api/workspaces/{workspace_id}/outline/approve", json={})
    assert missing_revision.status_code == 422

    revisited = client.get(f"/api/workspaces/{workspace_id}")
    assert revisited.status_code == 200
    assert revisited.json()["outline"]["status"] == "approved"
    assert client.get(f"/api/workspaces/{workspace_id}/outline/revisions").json()[0]["status"] == "approved"
