from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.infrastructure.parsing import ParserRegistry
from app.infrastructure.workspace.repository import WorkspaceRepository
from app.use_cases.workspace import ResearchWorkspaceService


class FakePdfParser:
    source_type = "pdf"
    supported_extensions = (".pdf",)

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[Path, str | None]] = []

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        self.calls.append((source_path, document_id))
        if self.error is not None:
            raise self.error
        return ParsedDocument(
            document_id=document_id or "document-version",
            source_path=str(source_path),
            source_type="pdf",
            units=[
                ParsedDocumentUnit(
                    content="A parsed paper paragraph.",
                    section="Introduction",
                    page_number=1,
                )
            ],
        )


def build_service(tmp_path: Path, parser: FakePdfParser) -> ResearchWorkspaceService:
    return ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([parser]),
        storage_root=tmp_path / "workspace-files",
    )


def test_workspace_upload_is_persisted_and_ready_for_evidence(tmp_path: Path) -> None:
    parser = FakePdfParser()
    service = build_service(tmp_path, parser)

    workspace = service.create_workspace(topic="Evidence attribution", report_language="zh")
    upload = service.upload_paper(workspace.id, filename="attention.pdf", content=b"%PDF-authorised")

    restored = service.get_workspace(workspace.id)
    assert restored.topic == "Evidence attribution"
    assert restored.report_language == "zh"
    assert len(restored.papers) == 1
    paper = restored.papers[0]
    assert paper.title == "attention"
    assert paper.selected is True
    assert paper.evidence_readiness == "ready"
    assert paper.evidence_eligible is True
    assert upload.operation.status == "succeeded"
    assert parser.calls[0][0].suffix == ".pdf"
    assert parser.calls[0][1] == paper.active_document_version_id
    assert service.evidence_papers(workspace.id)[0].id == paper.id


def test_workspace_state_survives_service_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.sqlite3"
    service = ResearchWorkspaceService(
        repository=WorkspaceRepository(database_path),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
    )
    workspace = service.create_workspace(topic="Restart persistence", report_language="zh")
    uploaded = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")

    restarted = ResearchWorkspaceService(
        repository=WorkspaceRepository(database_path),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
    )

    restored = restarted.get_workspace(workspace.id)
    assert restored.papers[0].id == uploaded.paper.id
    assert restored.papers[0].evidence_readiness == "ready"
    assert restarted.get_operation(uploaded.operation.id).status == "succeeded"


def test_restart_marks_queued_upload_interrupted_and_retryable(tmp_path: Path) -> None:
    database_path = tmp_path / "workspace.sqlite3"
    service = ResearchWorkspaceService(
        repository=WorkspaceRepository(database_path),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
    )
    workspace = service.create_workspace(topic="Interrupted processing", report_language="en")
    queued = service.start_upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")

    restarted = ResearchWorkspaceService(
        repository=WorkspaceRepository(database_path),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
    )

    interrupted_paper = restarted.get_workspace(workspace.id).papers[0]
    interrupted_operation = restarted.get_operation(queued.operation.id)
    assert interrupted_paper.evidence_readiness == "failed"
    assert interrupted_paper.retryable is True
    assert interrupted_operation.status == "interrupted"
    assert interrupted_operation.retry_action == "retry"


def test_workspace_upload_failure_is_retryable_and_not_evidence(tmp_path: Path) -> None:
    service = build_service(tmp_path, FakePdfParser(error=RuntimeError("provider unavailable")))
    workspace = service.create_workspace(topic="Failure handling", report_language="en")

    upload = service.upload_paper(workspace.id, filename="broken.pdf", content=b"%PDF-authorised")

    paper = service.get_workspace(workspace.id).papers[0]
    assert paper.selected is True
    assert paper.evidence_readiness == "failed"
    assert paper.failure_phase == "parsing"
    assert paper.retryable is True
    assert paper.evidence_eligible is False
    assert upload.operation.status == "failed"
    assert service.evidence_papers(workspace.id) == []


def test_failed_upload_can_be_retried_as_a_new_operation_and_version(tmp_path: Path) -> None:
    service = build_service(tmp_path, FakePdfParser(error=RuntimeError("provider unavailable")))
    workspace = service.create_workspace(topic="Retry handling", report_language="en")

    first = service.upload_paper(workspace.id, filename="broken.pdf", content=b"%PDF-authorised")
    retried = service.retry_paper(workspace.id, first.paper.id)

    assert retried.operation.id != first.operation.id
    assert retried.document_version_id != first.document_version_id
    assert retried.operation.status == "failed"
    assert retried.operation.retry_action == "retry"
    assert retried.paper.evidence_eligible is False


def test_removing_a_selected_paper_preserves_history_but_ends_eligibility(tmp_path: Path) -> None:
    service = build_service(tmp_path, FakePdfParser())
    workspace = service.create_workspace(topic="Selection boundary", report_language="en")
    upload = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")

    removed = service.remove_paper(workspace.id, upload.paper.id)

    assert removed.selected is False
    assert removed.evidence_readiness == "ready"
    assert removed.evidence_eligible is False
    assert service.get_workspace(workspace.id).papers[0].id == upload.paper.id
    assert service.evidence_papers(workspace.id) == []


def test_removed_paper_can_be_selected_again_without_losing_readiness(tmp_path: Path) -> None:
    service = build_service(tmp_path, FakePdfParser())
    workspace = service.create_workspace(topic="Selection boundary", report_language="en")
    upload = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")
    service.remove_paper(workspace.id, upload.paper.id)

    selected = service.select_paper(workspace.id, upload.paper.id)

    assert selected.selected is True
    assert selected.evidence_eligible is True
    assert service.evidence_papers(workspace.id)[0].id == upload.paper.id


def test_workspace_rejects_invalid_report_language(tmp_path: Path) -> None:
    service = build_service(tmp_path, FakePdfParser())

    with pytest.raises(ValueError, match="report_language"):
        service.create_workspace(topic="A topic", report_language="fr")
