"""Research Workspace API routes."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    InvalidPaperUploadError,
    PaperNotFoundError,
    PaperRAGError,
    WorkspaceArchivedError,
    WorkspaceNotFoundError,
    WorkspaceOperationNotFoundError,
)
from app.domain.workspace import ResearchPaper, ResearchWorkspace, WorkspaceOperation
from app.schemas import (
    ErrorResponse,
    ResearchPaperResponse,
    ResearchWorkspaceResponse,
    WorkspaceCreateRequest,
    WorkspaceOperationResponse,
    WorkspaceUploadResponse,
)
from app.use_cases.workspace import ResearchWorkspaceService

router = APIRouter()
_service: ResearchWorkspaceService | None = None


def get_workspace_service() -> ResearchWorkspaceService:
    global _service
    if _service is None:
        _service = ResearchWorkspaceService.from_paths()
    return _service


def _paper_response(paper: ResearchPaper) -> ResearchPaperResponse:
    return ResearchPaperResponse(
        id=paper.id,
        workspace_id=paper.workspace_id,
        title=paper.title,
        source_kind=paper.source_kind,
        original_filename=paper.original_filename,
        selected=paper.selected,
        evidence_readiness=paper.evidence_readiness,
        evidence_eligible=paper.evidence_eligible,
        active_document_version_id=paper.active_document_version_id,
        authors=paper.authors,
        year=paper.year,
        venue=paper.venue,
        failure_phase=paper.failure_phase,
        failure_message=paper.failure_message,
        retryable=paper.retryable,
    )


def _workspace_response(workspace: ResearchWorkspace) -> ResearchWorkspaceResponse:
    return ResearchWorkspaceResponse(
        id=workspace.id,
        topic=workspace.topic,
        report_language=workspace.report_language,
        state=workspace.state,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        papers=[_paper_response(paper) for paper in workspace.papers],
    )


def _operation_response(operation: WorkspaceOperation) -> WorkspaceOperationResponse:
    return WorkspaceOperationResponse(
        id=operation.id,
        workspace_id=operation.workspace_id,
        paper_id=operation.paper_id,
        operation_type=operation.operation_type,
        status=operation.status,
        phase=operation.phase,
        error_category=operation.error_category,
        error_message=operation.error_message,
        retry_action=operation.retry_action,
        completed_work=operation.completed_work,
        total_work=operation.total_work,
        started_at=operation.started_at,
        finished_at=operation.finished_at,
    )


def _error_response(exc: PaperRAGError | ValueError) -> JSONResponse:
    if isinstance(exc, (WorkspaceNotFoundError, PaperNotFoundError, WorkspaceOperationNotFoundError)):
        if isinstance(exc, WorkspaceNotFoundError):
            error = "workspace_not_found"
        elif isinstance(exc, PaperNotFoundError):
            error = "paper_not_found"
        else:
            error = "operation_not_found"
        status_code = 404
    elif isinstance(exc, InvalidPaperUploadError):
        error = "invalid_upload"
        status_code = 400
    elif isinstance(exc, WorkspaceArchivedError):
        error = "workspace_archived"
        status_code = 400
    else:
        error = "workspace_request_failed"
        status_code = 400
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "detail": str(exc), "error_type": type(exc).__name__},
    )


@router.post(
    "/workspaces",
    response_model=ResearchWorkspaceResponse,
    status_code=201,
    responses={"400": {"model": ErrorResponse}},
)
def create_workspace(request: WorkspaceCreateRequest) -> ResearchWorkspaceResponse:
    try:
        return _workspace_response(
            get_workspace_service().create_workspace(
                topic=request.topic,
                report_language=request.report_language,
            )
        )
    except (PaperRAGError, ValueError) as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.get("/workspaces", response_model=list[ResearchWorkspaceResponse])
def list_workspaces() -> list[ResearchWorkspaceResponse]:
    return [_workspace_response(workspace) for workspace in get_workspace_service().list_workspaces()]


@router.get(
    "/workspaces/{workspace_id}",
    response_model=ResearchWorkspaceResponse,
    responses={"404": {"model": ErrorResponse}},
)
def get_workspace(workspace_id: str) -> ResearchWorkspaceResponse:
    try:
        return _workspace_response(get_workspace_service().get_workspace(workspace_id))
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.post(
    "/workspaces/{workspace_id}/papers/upload",
    response_model=WorkspaceUploadResponse,
    status_code=202,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
async def upload_paper(
    workspace_id: str,
    file: UploadFile = File(...),
) -> WorkspaceUploadResponse:
    try:
        service = get_workspace_service()
        result = service.start_upload_paper(
            workspace_id,
            filename=file.filename or "",
            content=await file.read(),
        )
        service.enqueue_paper(result)
        return WorkspaceUploadResponse(
            paper=_paper_response(result.paper),
            operation=_operation_response(result.operation),
        )
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.post(
    "/workspaces/{workspace_id}/papers/{paper_id}/retry",
    response_model=WorkspaceUploadResponse,
    status_code=202,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def retry_paper(
    workspace_id: str,
    paper_id: str,
) -> WorkspaceUploadResponse:
    try:
        service = get_workspace_service()
        result = service.start_retry_paper(workspace_id, paper_id)
        service.enqueue_paper(result)
        return WorkspaceUploadResponse(
            paper=_paper_response(result.paper),
            operation=_operation_response(result.operation),
        )
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.delete(
    "/workspaces/{workspace_id}/papers/{paper_id}",
    response_model=ResearchPaperResponse,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def remove_paper(workspace_id: str, paper_id: str) -> ResearchPaperResponse:
    try:
        return _paper_response(get_workspace_service().remove_paper(workspace_id, paper_id))
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.post(
    "/workspaces/{workspace_id}/papers/{paper_id}/select",
    response_model=ResearchPaperResponse,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def select_paper(workspace_id: str, paper_id: str) -> ResearchPaperResponse:
    try:
        return _paper_response(get_workspace_service().select_paper(workspace_id, paper_id))
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.get(
    "/operations/{operation_id}",
    response_model=WorkspaceOperationResponse,
    responses={"404": {"model": ErrorResponse}},
)
def get_operation(operation_id: str) -> WorkspaceOperationResponse:
    try:
        return _operation_response(get_workspace_service().get_operation(operation_id))
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")
