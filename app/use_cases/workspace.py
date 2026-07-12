from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app.core.exceptions import (
    InvalidPaperUploadError,
    PaperNotFoundError,
    WorkspaceArchivedError,
    WorkspaceNotFoundError,
    WorkspaceOperationNotFoundError,
)
from app.core.paths import PathManager, get_paths
from app.domain.workspace import ResearchPaper, ResearchWorkspace, WorkspaceOperation
from app.infrastructure.chunking import ChunkBuilder
from app.infrastructure.parsing import MinerUParser, ParserRegistry
from app.infrastructure.workspace.repository import WorkspaceRepository


class UploadPaperResult:
    def __init__(
        self,
        paper: ResearchPaper,
        operation: WorkspaceOperation,
        *,
        source_path: Path,
        document_version_id: str,
    ) -> None:
        self.paper = paper
        self.operation = operation
        self.source_path = source_path
        self.document_version_id = document_version_id


class ResearchWorkspaceService:
    """Application seam for workspace creation and authorised paper upload."""

    def __init__(
        self,
        *,
        repository: WorkspaceRepository,
        parser_registry: ParserRegistry | None = None,
        chunk_builder: ChunkBuilder | None = None,
        storage_root: Path,
    ) -> None:
        self._repository = repository
        self._storage_root = storage_root
        self._parser_registry = parser_registry or ParserRegistry([MinerUParser()])
        self._chunk_builder = chunk_builder or ChunkBuilder()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="paperrag-workspace")
        self._repository.interrupt_unfinished_operations(timestamp=self._timestamp())

    @classmethod
    def from_paths(cls, paths: PathManager | None = None) -> ResearchWorkspaceService:
        resolved_paths = paths or get_paths()
        storage_root = resolved_paths.workspace_dir / "files"
        return cls(
            repository=WorkspaceRepository(resolved_paths.workspace_dir / "workspace.sqlite3"),
            storage_root=storage_root,
            parser_registry=ParserRegistry([MinerUParser(paths=resolved_paths)]),
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_workspace(self, *, topic: str, report_language: str) -> ResearchWorkspace:
        return self._repository.create_workspace(
            workspace_id=uuid.uuid4().hex,
            topic=topic,
            report_language=report_language,
            timestamp=self._timestamp(),
        )

    def list_workspaces(self) -> list[ResearchWorkspace]:
        return self._repository.list_workspaces()

    def get_workspace(self, workspace_id: str) -> ResearchWorkspace:
        workspace = self._repository.get_workspace(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace

    def _validate_upload(self, workspace_id: str, filename: str, content: bytes) -> tuple[ResearchWorkspace, str]:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        safe_filename = Path(filename.replace("\\", "/")).name
        if not safe_filename or Path(safe_filename).suffix.lower() != ".pdf":
            raise InvalidPaperUploadError("Only PDF uploads are supported.")
        if not content:
            raise InvalidPaperUploadError("The uploaded PDF is empty.")
        if b"%PDF-" not in content[:1024]:
            raise InvalidPaperUploadError("The uploaded file is not a valid PDF.")
        return workspace, safe_filename

    def start_upload_paper(self, workspace_id: str, *, filename: str, content: bytes) -> UploadPaperResult:
        _, safe_filename = self._validate_upload(workspace_id, filename, content)

        paper_id = uuid.uuid4().hex
        document_version_id = uuid.uuid4().hex
        operation_id = uuid.uuid4().hex
        paper_dir = self._storage_root / workspace_id / "papers" / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)
        source_path = paper_dir / safe_filename
        source_path.write_bytes(content)

        timestamp = self._timestamp()
        paper = self._repository.create_uploaded_paper(
            paper_id=paper_id,
            document_version_id=document_version_id,
            workspace_id=workspace_id,
            title=Path(safe_filename).stem,
            original_filename=safe_filename,
            storage_path=str(source_path),
            timestamp=timestamp,
        )
        operation = self._repository.create_operation(
            operation_id=operation_id,
            workspace_id=workspace_id,
            paper_id=paper_id,
            operation_type="import_paper",
            phase="importing",
            timestamp=timestamp,
        )
        return UploadPaperResult(
            paper=paper,
            operation=operation,
            source_path=source_path,
            document_version_id=document_version_id,
        )

    def upload_paper(self, workspace_id: str, *, filename: str, content: bytes) -> UploadPaperResult:
        result = self.start_upload_paper(workspace_id, filename=filename, content=content)
        return self.process_paper(result)

    def enqueue_paper(self, result: UploadPaperResult) -> None:
        self._executor.submit(self.process_paper, result)

    def process_paper(self, result: UploadPaperResult) -> UploadPaperResult:
        paper = result.paper
        operation = result.operation
        source_path = result.source_path
        workspace_id = paper.workspace_id
        paper_id = paper.id
        document_version_id = result.document_version_id

        current_phase = "importing"
        try:
            current_phase = "parsing"
            self._repository.update_operation(
                operation_id=operation.id,
                status="running",
                phase=current_phase,
                timestamp=self._timestamp(),
                retry_action=None,
            )
            parsed = self._parser_registry.parse(source_path, document_id=document_version_id)
            if not parsed.units:
                raise ValueError("the parser returned no paper content")
            parsed_artifact_path = source_path.parent / "parsed.json"
            parsed_artifact_path.write_text(
                json.dumps(parsed.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            current_phase = "indexing"
            self._repository.update_operation(
                operation_id=operation.id,
                status="running",
                phase=current_phase,
                timestamp=self._timestamp(),
                retry_action=None,
            )
            chunks = self._chunk_builder.build_chunks_from_parsed_document(parsed)
            if not chunks:
                raise ValueError("the chunker returned no paper chunks")
            (source_path.parent / "chunks.json").write_text(
                json.dumps(
                    [
                        {
                            "chunk_id": f"{document_version_id}__chunk_{index:04d}",
                            "document_version_id": document_version_id,
                            "section": chunk.section,
                            "content": chunk.content,
                            "title": chunk.title,
                            "authors": chunk.authors,
                            "year": chunk.year,
                            "venue": chunk.venue,
                        }
                        for index, chunk in enumerate(chunks)
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            paper = self._repository.mark_paper_ready(
                workspace_id=workspace_id,
                paper_id=paper_id,
                document_version_id=document_version_id,
                parsed_artifact_path=str(parsed_artifact_path),
                timestamp=self._timestamp(),
            )
            operation = self._repository.update_operation(
                operation_id=operation.id,
                status="succeeded",
                phase="ready",
                timestamp=self._timestamp(),
                completed_work=1,
                total_work=1,
                retry_action=None,
            )
        except Exception:
            safe_message = "PDF parsing failed. Retry the upload or provide another authorised PDF."
            paper = self._repository.mark_paper_failed(
                workspace_id=workspace_id,
                paper_id=paper_id,
                document_version_id=document_version_id,
                failure_phase=current_phase,
                failure_message=safe_message,
                timestamp=self._timestamp(),
            )
            operation = self._repository.update_operation(
                operation_id=operation.id,
                status="failed",
                phase=current_phase,
                timestamp=self._timestamp(),
                error_category="paper_processing_failed",
                error_message=safe_message,
                retry_action="retry",
            )

        if paper is None or operation is None:
            raise RuntimeError("workspace upload state could not be persisted")
        result.paper = paper
        result.operation = operation
        return result

    def start_retry_paper(self, workspace_id: str, paper_id: str) -> UploadPaperResult:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        paper = next((item for item in workspace.papers if item.id == paper_id), None)
        if paper is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        if paper.evidence_readiness != "failed" or not paper.retryable:
            raise InvalidPaperUploadError("This paper does not have a retryable processing failure.")
        source_path_value = self._repository.get_paper_storage_path(
            workspace_id=workspace_id,
            paper_id=paper_id,
        )
        if source_path_value is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        document_version_id = uuid.uuid4().hex
        operation_id = uuid.uuid4().hex
        timestamp = self._timestamp()
        paper = self._repository.begin_paper_retry(
            workspace_id=workspace_id,
            paper_id=paper_id,
            document_version_id=document_version_id,
            timestamp=timestamp,
        )
        operation = self._repository.create_operation(
            operation_id=operation_id,
            workspace_id=workspace_id,
            paper_id=paper_id,
            operation_type="retry_paper_import",
            phase="importing",
            timestamp=timestamp,
        )
        if paper is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        return UploadPaperResult(
            paper=paper,
            operation=operation,
            source_path=Path(source_path_value),
            document_version_id=document_version_id,
        )

    def retry_paper(self, workspace_id: str, paper_id: str) -> UploadPaperResult:
        return self.process_paper(self.start_retry_paper(workspace_id, paper_id))

    def _set_paper_selection(self, workspace_id: str, paper_id: str, *, selected: bool) -> ResearchPaper:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        paper = next((item for item in workspace.papers if item.id == paper_id), None)
        if paper is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        updated = self._repository.set_paper_selected(
            workspace_id=workspace_id,
            paper_id=paper_id,
            selected=selected,
            timestamp=self._timestamp(),
        )
        if updated is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        return updated

    def remove_paper(self, workspace_id: str, paper_id: str) -> ResearchPaper:
        return self._set_paper_selection(workspace_id, paper_id, selected=False)

    def select_paper(self, workspace_id: str, paper_id: str) -> ResearchPaper:
        return self._set_paper_selection(workspace_id, paper_id, selected=True)

    def evidence_papers(self, workspace_id: str) -> list[ResearchPaper]:
        return [paper for paper in self.get_workspace(workspace_id).papers if paper.evidence_eligible]

    def get_operation(self, operation_id: str) -> WorkspaceOperation:
        operation = self._repository.get_operation(operation_id)
        if operation is None:
            raise WorkspaceOperationNotFoundError(operation_id)
        return operation
