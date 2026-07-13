"""Research Workspace API routes."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    InvalidOutlineError,
    InvalidPaperUploadError,
    OutlineNotFoundError,
    OutlineUnavailableError,
    PaperNotFoundError,
    PaperRAGError,
    WorkspaceArchivedError,
    WorkspaceNotFoundError,
    WorkspaceOperationNotFoundError,
)
from app.domain.outline import OutlineSection, ReportOutline
from app.domain.workspace import ResearchPaper, ResearchWorkspace, WorkspaceOperation
from app.schemas import (
    ErrorResponse,
    OutlineApproveRequest,
    OutlineSaveRequest,
    OutlineSectionResponse,
    ReportOutlineResponse,
    ResearchPaperResponse,
    ResearchWorkspaceResponse,
    WorkspaceCreateRequest,
    WorkspaceDiscoveryRequest,
    WorkspaceDiscoveryResponse,
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
        next_action=paper.next_action,
        doi=paper.doi,
        abstract=paper.abstract,
        published_at=paper.published_at,
        source_updated_at=paper.source_updated_at,
        source_url=paper.source_url,
        pdf_url=paper.pdf_url,
        is_open_access=paper.is_open_access,
        license=paper.license,
        source_links=paper.source_links,
        discovery_query=paper.discovery_query,
        discovered_at=paper.discovered_at,
    )


def _workspace_response(
    workspace: ResearchWorkspace,
    operations: list[WorkspaceOperation] | None = None,
    outline: ReportOutline | None = None,
) -> ResearchWorkspaceResponse:
    return ResearchWorkspaceResponse(
        id=workspace.id,
        topic=workspace.topic,
        report_language=workspace.report_language,
        state=workspace.state,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        papers=[_paper_response(paper) for paper in workspace.papers],
        operations=[_operation_response(operation) for operation in (operations or [])],
        outline=_outline_response(outline) if outline else None,
    )


def _outline_response(outline: ReportOutline) -> ReportOutlineResponse:
    return ReportOutlineResponse(
        id=outline.id,
        workspace_id=outline.workspace_id,
        revision_number=outline.revision_number,
        status=outline.status,
        title=outline.title,
        research_question=outline.research_question,
        sections=[
            OutlineSectionResponse(id=section.id, title=section.title, description=section.description)
            for section in outline.sections
        ],
        evidence_paper_ids=outline.evidence_paper_ids,
        created_at=outline.created_at,
        updated_at=outline.updated_at,
        approved_at=outline.approved_at,
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
    elif isinstance(exc, OutlineNotFoundError):
        error = "outline_not_found"
        status_code = 404
    elif isinstance(exc, OutlineUnavailableError):
        error = "outline_unavailable"
        status_code = 400
    elif isinstance(exc, InvalidOutlineError):
        error = "invalid_outline"
        status_code = 400
    else:
        error = "workspace_request_failed"
        status_code = 400
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "detail": str(exc),
            "error_type": type(exc).__name__,
            "next_action": getattr(exc, "next_action", None),
        },
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
    service = get_workspace_service()
    return [
        _workspace_response(workspace, service.list_operations(workspace.id), service.get_outline(workspace.id))
        for workspace in service.list_workspaces()
    ]


@router.get(
    "/workspaces/{workspace_id}",
    response_model=ResearchWorkspaceResponse,
    responses={"404": {"model": ErrorResponse}},
)
def get_workspace(workspace_id: str) -> ResearchWorkspaceResponse:
    try:
        service = get_workspace_service()
        workspace = service.get_workspace(workspace_id)
        return _workspace_response(
            workspace,
            service.list_operations(workspace_id),
            service.get_outline(workspace_id),
        )
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.get(
    "/workspaces/{workspace_id}/outline",
    response_model=ReportOutlineResponse,
    responses={"404": {"model": ErrorResponse}},
)
def get_workspace_outline(workspace_id: str) -> ReportOutlineResponse:
    try:
        outline = get_workspace_service().get_outline(workspace_id)
        if outline is None:
            raise OutlineNotFoundError(workspace_id)
        return _outline_response(outline)
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.get(
    "/workspaces/{workspace_id}/outline/revisions",
    response_model=list[ReportOutlineResponse],
    responses={"404": {"model": ErrorResponse}},
)
def list_workspace_outline_revisions(workspace_id: str) -> list[ReportOutlineResponse]:
    try:
        return [_outline_response(outline) for outline in get_workspace_service().list_outline_revisions(workspace_id)]
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.post(
    "/workspaces/{workspace_id}/outline/generate",
    response_model=WorkspaceOperationResponse,
    status_code=202,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def generate_workspace_outline(workspace_id: str) -> WorkspaceOperationResponse:
    try:
        service = get_workspace_service()
        operation = service.start_outline_generation(workspace_id)
        service.enqueue_outline_generation(operation)
        return _operation_response(operation)
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.put(
    "/workspaces/{workspace_id}/outline",
    response_model=ReportOutlineResponse,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def save_workspace_outline(workspace_id: str, request: OutlineSaveRequest) -> ReportOutlineResponse:
    try:
        sections = [
            OutlineSection(id=section.id, title=section.title, description=section.description)
            for section in request.sections
        ]
        return _outline_response(
            get_workspace_service().save_outline(
                workspace_id,
                title=request.title,
                research_question=request.research_question,
                sections=sections,
                revision_id=request.revision_id,
            )
        )
    except (PaperRAGError, ValueError) as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.post(
    "/workspaces/{workspace_id}/outline/approve",
    response_model=ReportOutlineResponse,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def approve_workspace_outline(
    workspace_id: str,
    request: OutlineApproveRequest,
) -> ReportOutlineResponse:
    try:
        return _outline_response(
            get_workspace_service().approve_outline(
                workspace_id,
                revision_id=request.revision_id,
            )
        )
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.post(
    "/workspaces/{workspace_id}/papers/discover",
    response_model=WorkspaceDiscoveryResponse,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def discover_papers(
    workspace_id: str,
    request: WorkspaceDiscoveryRequest,
) -> WorkspaceDiscoveryResponse:
    try:
        result = get_workspace_service().discover_papers(
            workspace_id,
            query=request.query,
            provider=request.provider,
            page=request.page,
            per_page=request.per_page,
        )
        return WorkspaceDiscoveryResponse(
            query=result.query,
            status=result.status,
            candidates=[_paper_response(paper) for paper in result.candidates],
            page=result.page,
            per_page=result.per_page,
            total_count=result.total_count,
            next_page=result.next_page,
            error_message=result.error_message,
            retryable=result.retryable,
        )
    except (PaperRAGError, ValueError) as exc:
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
    candidate_id: str | None = Form(default=None),
) -> WorkspaceUploadResponse:
    try:
        service = get_workspace_service()
        result = service.start_upload_paper(
            workspace_id,
            filename=file.filename or "",
            content=await file.read(),
            candidate_id=candidate_id,
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
    "/workspaces/{workspace_id}/papers/{paper_id}/import",
    response_model=WorkspaceUploadResponse,
    status_code=202,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def import_discovered_paper(
    workspace_id: str,
    paper_id: str,
    replace: bool = False,
) -> WorkspaceUploadResponse:
    try:
        service = get_workspace_service()
        result = service.start_import_discovered_paper(workspace_id, paper_id, replace=replace)
        service.enqueue_paper(result)
        return WorkspaceUploadResponse(
            paper=_paper_response(result.paper),
            operation=_operation_response(result.operation) if result.operation else None,
        )
    except (PaperRAGError, ValueError) as exc:
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


@router.post(
    "/operations/{operation_id}/retry",
    response_model=WorkspaceOperationResponse,
    status_code=202,
    responses={"400": {"model": ErrorResponse}, "404": {"model": ErrorResponse}},
)
def retry_operation(operation_id: str) -> WorkspaceOperationResponse:
    try:
        return _operation_response(get_workspace_service().retry_operation(operation_id))
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")


@router.get(
    "/workspaces/{workspace_id}/operations",
    response_model=list[WorkspaceOperationResponse],
    responses={"404": {"model": ErrorResponse}},
)
def list_workspace_operations(workspace_id: str) -> list[WorkspaceOperationResponse]:
    try:
        return [
            _operation_response(operation)
            for operation in get_workspace_service().list_operations(workspace_id)
        ]
    except PaperRAGError as exc:
        return _error_response(exc)
    raise AssertionError("unreachable")
