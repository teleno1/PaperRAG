from __future__ import annotations

from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.routes import workspaces as workspace_route
from app.core.exceptions import ReportUnavailableError
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
            metadata={"title": source_path.stem, "year": "2025"},
            units=[
                ParsedDocumentUnit(
                    content="Evidence attribution improves traceability across research papers.",
                    section="Findings",
                    page_number=2,
                )
            ],
        )


def build_service(tmp_path: Path, report_generator=None) -> ResearchWorkspaceService:
    return ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
        report_generator=report_generator,
    )


def prepare_approved_outline(service: ResearchWorkspaceService, workspace_id: str):
    outline = service.generate_outline(workspace_id)
    return service.approve_outline(workspace_id, revision_id=outline.id)


def test_report_generation_uses_ready_selected_papers_and_persists_citations(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    workspace = service.create_workspace(topic="Evidence attribution", report_language="en")
    uploaded = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")
    prepare_approved_outline(service, workspace.id)

    report = service.generate_report(workspace.id)

    assert report.workspace_id == workspace.id
    assert report.outline_revision_id == service.get_outline(workspace.id).id
    assert report.evidence_coverage.included_paper_ids == [uploaded.paper.id]
    assert report.evidence_coverage.excluded_papers == []
    claims = [claim for section in report.sections for claim in section.claims if claim.citations]
    assert claims
    assert all(citation.source_chunk_ids for claim in claims for citation in claim.citations)
    citation_id = claims[0].citations[0].id

    restarted = build_service(tmp_path)
    restored = restarted.get_report_draft(workspace.id)
    assert restored is not None
    assert restored.id == report.id
    assert restored.sections[0].claims[0].citations[0].id == citation_id


def test_mixed_readiness_requires_explicit_ready_subset_and_records_exclusion(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    workspace = service.create_workspace(topic="Evidence attribution", report_language="zh")
    ready = service.upload_paper(workspace.id, filename="ready.pdf", content=b"%PDF-ready")
    prepare_approved_outline(service, workspace.id)
    pending = service.start_upload_paper(workspace.id, filename="pending.pdf", content=b"%PDF-pending")

    with pytest.raises(ReportUnavailableError, match="ready subset"):
        service.generate_report(workspace.id)

    report = service.generate_report(workspace.id, use_ready_subset=True)

    assert report.evidence_coverage.included_paper_ids == [ready.paper.id]
    assert report.evidence_coverage.excluded_papers == [
        {"paper_id": pending.paper.id, "reason": "importing"}
    ]


def test_failed_generation_keeps_previous_draft_and_records_recoverable_operation(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    workspace = service.create_workspace(topic="Evidence attribution", report_language="en")
    service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")
    outline = prepare_approved_outline(service, workspace.id)
    first = service.generate_report(workspace.id)

    class FailingGenerator:
        def generate(self, **_: object):
            raise RuntimeError("controlled generator failure")

    failing = build_service(tmp_path, report_generator=FailingGenerator())
    operation = failing.start_report_generation(workspace.id)
    with pytest.raises(ReportUnavailableError, match="generation failed"):
        failing.process_report_generation(operation.id, workspace.id)

    restored = failing.get_report_draft(workspace.id)
    assert restored is not None
    assert restored.id == first.id
    assert restored.outline_revision_id == outline.id
    assert failing.get_operation(operation.id).status == "failed"


def test_report_api_exposes_stable_claim_citations_and_saves_browser_edits(tmp_path: Path, monkeypatch) -> None:
    service = build_service(tmp_path)
    monkeypatch.setattr(workspace_route, "get_workspace_service", lambda: service)
    client = TestClient(app)
    workspace_id = client.post(
        "/api/workspaces",
        json={"topic": "Evidence attribution", "report_language": "zh"},
    ).json()["id"]
    uploaded = client.post(
        f"/api/workspaces/{workspace_id}/papers/upload",
        files={"file": ("paper.pdf", b"%PDF-authorised", "application/pdf")},
    ).json()
    for _ in range(50):
        if client.get(f"/api/operations/{uploaded['operation']['id']}").json()["status"] == "succeeded":
            break
        time.sleep(0.01)
    outline = client.post(f"/api/workspaces/{workspace_id}/outline/generate").json()
    for _ in range(50):
        if client.get(f"/api/operations/{outline['id']}").json()["status"] == "succeeded":
            break
        time.sleep(0.01)
    current_outline = client.get(f"/api/workspaces/{workspace_id}/outline").json()
    assert client.post(
        f"/api/workspaces/{workspace_id}/outline/approve",
        json={"revision_id": current_outline["id"]},
    ).status_code == 200

    started = client.post(f"/api/workspaces/{workspace_id}/report/generate", json={})
    assert started.status_code == 202
    for _ in range(50):
        if client.get(f"/api/operations/{started.json()['id']}").json()["status"] == "succeeded":
            break
        time.sleep(0.01)
    report = client.get(f"/api/workspaces/{workspace_id}/report").json()
    claim = next(
        claim
        for section in report["sections"]
        for claim in section["claims"]
        if claim["citations"]
    )
    citation_id = claim["citations"][0]["id"]
    claim["text"] = "用户编辑后的报告 Claim"
    saved = client.put(f"/api/workspaces/{workspace_id}/report", json=report)
    assert saved.status_code == 200
    assert saved.json()["sections"][0]["claims"][0]["citations"][0]["id"] == citation_id
    assert client.get(f"/api/workspaces/{workspace_id}").json()["report"]["id"] == report["id"]
