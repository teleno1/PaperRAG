from __future__ import annotations

import json
import re
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from app.core.exceptions import (
    InvalidOutlineError,
    InvalidPaperUploadError,
    OutlineNotFoundError,
    OutlineUnavailableError,
    PaperNotFoundError,
    WorkspaceArchivedError,
    WorkspaceNotFoundError,
    WorkspaceOperationNotFoundError,
)
from app.core.config import get_settings
from app.core.paths import PathManager, get_paths
from app.domain.outline import OutlineSection, ReportOutline
from app.domain.workspace import (
    DiscoveryResult,
    ResearchPaper,
    ResearchWorkspace,
    WorkspaceOperation,
)
from app.infrastructure.chunking import ChunkBuilder
from app.infrastructure.discovery import (
    ArxivProvider,
    DiscoveryProviderError,
    OpenAlexProvider,
    PaperDiscoveryProvider,
    PdfDownloadError,
    PdfDownloadResult,
    PdfDownloader,
    RequestsPdfDownloader,
)
from app.infrastructure.parsing import MinerUParser, ParserRegistry
from app.infrastructure.workspace.repository import WorkspaceRepository


class UploadPaperResult:
    def __init__(
        self,
        paper: ResearchPaper,
        operation: WorkspaceOperation | None,
        *,
        source_path: Path,
        document_version_id: str,
        download_url: str | None = None,
    ) -> None:
        self.paper = paper
        self.operation = operation
        self.source_path = source_path
        self.document_version_id = document_version_id
        self.download_url = download_url
        self.download_result: PdfDownloadResult | None = None


class ResearchWorkspaceService:
    """Application seam for workspace preparation and outline lifecycle."""

    def __init__(
        self,
        *,
        repository: WorkspaceRepository,
        parser_registry: ParserRegistry | None = None,
        chunk_builder: ChunkBuilder | None = None,
        storage_root: Path,
        discovery_providers: Mapping[str, PaperDiscoveryProvider] | None = None,
        pdf_downloader: PdfDownloader | None = None,
    ) -> None:
        self._repository = repository
        self._storage_root = storage_root
        self._parser_registry = parser_registry or ParserRegistry([MinerUParser()])
        self._chunk_builder = chunk_builder or ChunkBuilder()
        self._discovery_providers = dict(discovery_providers or {"openalex": OpenAlexProvider()})
        self._pdf_downloader = pdf_downloader or RequestsPdfDownloader()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="paperrag-workspace")
        self._repository.interrupt_unfinished_operations(timestamp=self._timestamp())

    @classmethod
    def from_paths(cls, paths: PathManager | None = None) -> ResearchWorkspaceService:
        resolved_paths = paths or get_paths()
        storage_root = resolved_paths.workspace_dir / "files"
        settings = get_settings()
        return cls(
            repository=WorkspaceRepository(resolved_paths.workspace_dir / "workspace.sqlite3"),
            storage_root=storage_root,
            parser_registry=ParserRegistry([MinerUParser(paths=resolved_paths)]),
            discovery_providers={
                "openalex": OpenAlexProvider(api_key=settings.models.openalex_api_key),
                "arxiv": ArxivProvider(),
            },
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

    @staticmethod
    def _candidate_filename(title: str, provider_id: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", title).strip("-.")[:80] or provider_id
        return f"{slug}.pdf"

    def _version_source_path(self, workspace_id: str, paper_id: str, document_version_id: str, filename: str) -> Path:
        return self._storage_root / workspace_id / "papers" / paper_id / "versions" / document_version_id / filename

    def discover_papers(
        self,
        workspace_id: str,
        *,
        query: str | None = None,
        provider: str = "openalex",
        page: int = 1,
        per_page: int = 10,
    ) -> DiscoveryResult:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        normalized_query = (query or workspace.topic).strip()
        if not normalized_query:
            raise ValueError("discovery query must not be empty")
        selected_provider = self._discovery_providers.get(provider)
        if selected_provider is None:
            raise ValueError(f"unknown discovery provider: {provider}")
        try:
            result = selected_provider.search(normalized_query, page=page, per_page=per_page)
        except DiscoveryProviderError as exc:
            return DiscoveryResult(
                status="retryable_error" if exc.retryable else "failed",
                provider=provider,
                query=normalized_query,
                candidates=[paper for paper in workspace.papers if paper.source_kind == "discovery"],
                page=page,
                per_page=per_page,
                error_message=str(exc),
                retryable=exc.retryable,
            )
        candidates: list[ResearchPaper] = []
        seen_ids: set[str] = set()
        for candidate in result.candidates:
            paper = self._repository.upsert_discovered_paper(
                paper_id=uuid.uuid4().hex,
                workspace_id=workspace_id,
                candidate=candidate,
                original_filename=self._candidate_filename(candidate.title, candidate.provider_id),
                discovery_query=normalized_query,
                timestamp=self._timestamp(),
            )
            if paper.id not in seen_ids:
                candidates.append(paper)
                seen_ids.add(paper.id)
            else:
                candidates = [paper if item.id == paper.id else item for item in candidates]
        return DiscoveryResult(
            status="succeeded" if candidates else "empty",
            provider=result.provider,
            query=normalized_query,
            candidates=candidates,
            page=result.page,
            per_page=result.per_page,
            total_count=result.total_count,
            next_page=result.next_page,
        )

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

    def start_upload_paper(
        self,
        workspace_id: str,
        *,
        filename: str,
        content: bytes,
        candidate_id: str | None = None,
    ) -> UploadPaperResult:
        workspace, safe_filename = self._validate_upload(workspace_id, filename, content)

        if candidate_id is not None:
            candidate = next((paper for paper in workspace.papers if paper.id == candidate_id), None)
            if candidate is None:
                raise PaperNotFoundError(workspace_id, candidate_id)
            if candidate.source_kind != "discovery":
                raise InvalidPaperUploadError("The authorised upload target must be a discovered candidate.")
            document_version_id = uuid.uuid4().hex
            operation_id = uuid.uuid4().hex
            source_path = self._version_source_path(workspace_id, candidate_id, document_version_id, safe_filename)
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(content)
            timestamp = self._timestamp()
            paper = self._repository.begin_authorised_upload(
                workspace_id=workspace_id,
                paper_id=candidate_id,
                document_version_id=document_version_id,
                original_filename=safe_filename,
                storage_path=str(source_path),
                timestamp=timestamp,
            )
            operation = self._repository.create_operation(
                operation_id=operation_id,
                workspace_id=workspace_id,
                paper_id=candidate_id,
                operation_type="import_authorised_paper",
                phase="importing",
                timestamp=timestamp,
            )
            if paper is None:
                raise PaperNotFoundError(workspace_id, candidate_id)
            return UploadPaperResult(
                paper=paper,
                operation=operation,
                source_path=source_path,
                document_version_id=document_version_id,
            )

        paper_id = uuid.uuid4().hex
        document_version_id = uuid.uuid4().hex
        operation_id = uuid.uuid4().hex
        source_path = self._version_source_path(workspace_id, paper_id, document_version_id, safe_filename)
        source_path.parent.mkdir(parents=True, exist_ok=True)
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

    def upload_paper(
        self,
        workspace_id: str,
        *,
        filename: str,
        content: bytes,
        candidate_id: str | None = None,
    ) -> UploadPaperResult:
        result = self.start_upload_paper(
            workspace_id,
            filename=filename,
            content=content,
            candidate_id=candidate_id,
        )
        return self.process_paper(result)

    def enqueue_paper(self, result: UploadPaperResult) -> None:
        if result.operation is not None:
            self._executor.submit(self.process_paper, result)

    def process_paper(self, result: UploadPaperResult) -> UploadPaperResult:
        paper = result.paper
        operation = result.operation
        source_path = result.source_path
        workspace_id = paper.workspace_id
        paper_id = paper.id
        document_version_id = result.document_version_id

        if operation is None:
            return result

        current_phase = "importing"
        try:
            self._repository.update_operation(
                operation_id=operation.id,
                status="running",
                phase=current_phase,
                timestamp=self._timestamp(),
                retry_action=None,
            )
            if result.download_url:
                result.download_result = self._pdf_downloader.download(result.download_url, source_path)
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
            version_artifact_dir = source_path.parent
            parsed_artifact_path = version_artifact_dir / "parsed.json"
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
            (version_artifact_dir / "chunks.json").write_text(
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
                final_source_url=result.download_result.final_url if result.download_result else None,
                content_sha256=result.download_result.content_sha256 if result.download_result else None,
                imported_at=result.download_result.downloaded_at if result.download_result else None,
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
        except PdfDownloadError as exc:
            safe_message = str(exc)
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
                error_category=exc.category,
                error_message=safe_message,
                retry_action="retry",
            )
        except Exception:
            safe_message = "PDF parsing failed. Retry the import or provide another authorised PDF."
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

    def start_import_discovered_paper(
        self,
        workspace_id: str,
        paper_id: str,
        *,
        replace: bool = False,
    ) -> UploadPaperResult:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        paper = next((item for item in workspace.papers if item.id == paper_id), None)
        if paper is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        if paper.source_kind != "discovery":
            raise InvalidPaperUploadError("Only discovered candidates can use automatic PDF import.")
        if paper.evidence_readiness == "ready" and not replace:
            raise InvalidPaperUploadError(
                "This discovered paper is already ready for evidence; use replace=true to create a new document version."
            )
        can_auto_import = paper.pdf_url and (paper.is_open_access is True or paper.provider == "arxiv")
        if not can_auto_import:
            updated = self._repository.mark_paper_awaiting_authorised_file(
                workspace_id=workspace_id,
                paper_id=paper_id,
                timestamp=self._timestamp(),
            )
            if updated is None:
                raise PaperNotFoundError(workspace_id, paper_id)
            return UploadPaperResult(
                paper=updated,
                operation=None,
                source_path=self._version_source_path(workspace_id, paper_id, "awaiting", updated.original_filename),
                document_version_id="",
            )

        document_version_id = uuid.uuid4().hex
        operation_id = uuid.uuid4().hex
        source_path = self._version_source_path(workspace_id, paper_id, document_version_id, paper.original_filename)
        source_path.parent.mkdir(parents=True, exist_ok=True)
        updated = self._repository.begin_discovered_import(
            workspace_id=workspace_id,
            paper_id=paper_id,
            document_version_id=document_version_id,
            storage_path=str(source_path),
            requested_source_url=paper.pdf_url,
            timestamp=self._timestamp(),
        )
        if updated is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        operation = self._repository.create_operation(
            operation_id=operation_id,
            workspace_id=workspace_id,
            paper_id=paper_id,
            operation_type="import_discovered_paper",
            phase="importing",
            timestamp=self._timestamp(),
        )
        return UploadPaperResult(
            paper=updated,
            operation=operation,
            source_path=source_path,
            document_version_id=document_version_id,
            download_url=paper.pdf_url,
        )

    def import_discovered_paper(
        self,
        workspace_id: str,
        paper_id: str,
        *,
        replace: bool = False,
    ) -> UploadPaperResult:
        result = self.start_import_discovered_paper(workspace_id, paper_id, replace=replace)
        return self.process_paper(result)

    def start_retry_paper(self, workspace_id: str, paper_id: str) -> UploadPaperResult:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        paper = next((item for item in workspace.papers if item.id == paper_id), None)
        if paper is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        if paper.evidence_readiness != "failed" or not paper.retryable:
            raise InvalidPaperUploadError("This paper does not have a retryable processing failure.")
        previous_source_path = self._repository.get_paper_storage_path(
            workspace_id=workspace_id,
            paper_id=paper_id,
        )
        if previous_source_path is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        document_version_id = uuid.uuid4().hex
        source_path = self._version_source_path(
            workspace_id,
            paper_id,
            document_version_id,
            paper.original_filename,
        )
        source_path.parent.mkdir(parents=True, exist_ok=True)
        if paper.source_kind == "upload":
            shutil.copy2(previous_source_path, source_path)
        operation_id = uuid.uuid4().hex
        timestamp = self._timestamp()
        paper = self._repository.begin_paper_retry(
            workspace_id=workspace_id,
            paper_id=paper_id,
            document_version_id=document_version_id,
            storage_path=str(source_path),
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
            source_path=source_path,
            document_version_id=document_version_id,
            download_url=paper.pdf_url if paper.source_kind == "discovery" else None,
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

    def list_operations(self, workspace_id: str) -> list[WorkspaceOperation]:
        self.get_workspace(workspace_id)
        return self._repository.list_operations(workspace_id)

    def retry_operation(self, operation_id: str) -> WorkspaceOperation:
        operation = self.get_operation(operation_id)
        if operation.operation_type != "generate_outline":
            raise InvalidOutlineError("Only failed Report Outline generation operations can be retried here.")
        if operation.status not in {"failed", "interrupted"}:
            raise InvalidOutlineError("Only failed or interrupted Report Outline operations can be retried.")
        retry = self.start_outline_generation(operation.workspace_id)
        self.enqueue_outline_generation(retry)
        return retry

    def get_outline(self, workspace_id: str) -> ReportOutline | None:
        self.get_workspace(workspace_id)
        return self._repository.get_current_outline(workspace_id)

    def list_outline_revisions(self, workspace_id: str) -> list[ReportOutline]:
        self.get_workspace(workspace_id)
        return self._repository.list_outline_revisions(workspace_id)

    def _default_outline(self, workspace: ResearchWorkspace, evidence_paper_ids: list[str]) -> tuple[str, str, list[OutlineSection]]:
        if workspace.report_language == "en":
            title = f"Literature review outline: {workspace.topic}"
            research_question = (
                f"Which methods and findings define research on {workspace.topic}, "
                "and where do the studies differ or leave evidence gaps?"
            )
            sections = [
                OutlineSection("research-question", "Research question and scope", "Define the question, concepts, and boundaries of this review."),
                OutlineSection("methods-findings", "Methods and findings", "Summarise the methods and main findings supported by the selected papers."),
                OutlineSection("comparison", "Comparison across studies", "Compare assumptions, data, methods, and findings across the evidence set."),
                OutlineSection("limitations-gaps", "Limitations and research gaps", "Identify limitations and open questions that the current evidence does not resolve."),
                OutlineSection("conclusion", "Conclusion", "Synthesize the answer to the research question without adding unsupported claims."),
                OutlineSection("references", "References", "List the selected papers used by the approved outline."),
            ]
        else:
            title = f"{workspace.topic}：文献综述大纲"
            research_question = (
                f"围绕“{workspace.topic}”，现有研究采用了哪些方法、得到什么发现，"
                "不同研究之间有何差异，还存在哪些证据缺口？"
            )
            sections = [
                OutlineSection("research-question", "研究问题与范围", "明确研究问题、核心概念和本次综述的边界。"),
                OutlineSection("methods-findings", "方法与主要发现", "概括 Selected Papers 支持的方法、数据和主要发现。"),
                OutlineSection("comparison", "研究比较", "比较不同研究的假设、数据、方法和结论。"),
                OutlineSection("limitations-gaps", "局限与研究缺口", "指出当前证据能够支持的范围、局限和仍待回答的问题。"),
                OutlineSection("conclusion", "结论", "在不添加无依据事实的前提下回答研究问题并综合主要结论。"),
                OutlineSection("references", "参考文献", "列出本次批准大纲所使用的 Selected Papers。"),
            ]
        return title, research_question, sections

    def start_outline_generation(self, workspace_id: str) -> WorkspaceOperation:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        evidence_paper_ids = [paper.id for paper in workspace.papers if paper.evidence_eligible]
        if not evidence_paper_ids:
            raise OutlineUnavailableError(
                workspace_id,
                "select and process at least one Selected Paper until Evidence Readiness is ready",
            )

        return self._repository.create_operation(
            operation_id=uuid.uuid4().hex,
            workspace_id=workspace_id,
            paper_id=None,
            operation_type="generate_outline",
            phase="generating",
            timestamp=self._timestamp(),
        )

    def enqueue_outline_generation(self, operation: WorkspaceOperation) -> None:
        self._executor.submit(self.process_outline_generation, operation.id, operation.workspace_id)

    def process_outline_generation(self, operation_id: str, workspace_id: str) -> ReportOutline:
        operation = self.get_operation(operation_id)
        try:
            self._repository.update_operation(
                operation_id=operation.id,
                status="running",
                phase="generating",
                timestamp=self._timestamp(),
                retry_action=None,
            )
            workspace = self.get_workspace(workspace_id)
            evidence_paper_ids = [paper.id for paper in workspace.papers if paper.evidence_eligible]
            if not evidence_paper_ids:
                raise OutlineUnavailableError(
                    workspace_id,
                    "select and process at least one Selected Paper until Evidence Readiness is ready",
                )
            title, research_question, sections = self._default_outline(workspace, evidence_paper_ids)
            outline = self._repository.create_outline_revision(
                outline_id=uuid.uuid4().hex,
                workspace_id=workspace_id,
                status="draft",
                title=title,
                research_question=research_question,
                sections=sections,
                evidence_paper_ids=evidence_paper_ids,
                timestamp=self._timestamp(),
            )
            self._repository.update_operation(
                operation_id=operation.id,
                status="succeeded",
                phase="draft_ready",
                timestamp=self._timestamp(),
                completed_work=1,
                total_work=1,
                retry_action=None,
            )
            return outline
        except Exception as exc:
            self._repository.update_operation(
                operation_id=operation.id,
                status="failed",
                phase="generating",
                timestamp=self._timestamp(),
                error_category="outline_generation_failed",
                error_message="Report Outline generation failed. Retry after checking the selected evidence.",
                retry_action="retry",
            )
            if isinstance(exc, (InvalidOutlineError, OutlineUnavailableError)):
                raise
            raise InvalidOutlineError("Report Outline generation failed. Retry after checking the selected evidence.") from exc

    def generate_outline(self, workspace_id: str) -> ReportOutline:
        """Synchronous application seam retained for use-case tests and callers."""

        operation = self.start_outline_generation(workspace_id)
        return self.process_outline_generation(operation.id, workspace_id)

    def save_outline(
        self,
        workspace_id: str,
        *,
        title: str,
        research_question: str,
        sections: list[OutlineSection],
        revision_id: str | None = None,
    ) -> ReportOutline:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        current = self._repository.get_current_outline(workspace_id)
        if current is None:
            raise OutlineNotFoundError(workspace_id)
        if revision_id and revision_id != current.id:
            raise InvalidOutlineError("Only the current Report Outline revision can be edited.")
        try:
            candidate = ReportOutline(
                id=current.id,
                workspace_id=workspace_id,
                revision_number=current.revision_number,
                status="draft",
                title=title,
                research_question=research_question,
                sections=sections,
                evidence_paper_ids=current.evidence_paper_ids,
                created_at=current.created_at,
                updated_at=current.updated_at,
            )
        except ValueError as exc:
            raise InvalidOutlineError(str(exc)) from exc

        if current.status == "draft":
            updated = self._repository.update_draft_outline(
                outline_id=current.id,
                workspace_id=workspace_id,
                title=candidate.title,
                research_question=candidate.research_question,
                sections=candidate.sections,
                timestamp=self._timestamp(),
            )
        else:
            updated = self._repository.create_outline_revision(
                outline_id=uuid.uuid4().hex,
                workspace_id=workspace_id,
                status="draft",
                title=candidate.title,
                research_question=candidate.research_question,
                sections=candidate.sections,
                evidence_paper_ids=current.evidence_paper_ids,
                timestamp=self._timestamp(),
            )
        if updated is None:
            raise InvalidOutlineError("The current Report Outline could not be saved.")
        return updated

    def approve_outline(self, workspace_id: str, *, revision_id: str) -> ReportOutline:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        current = self._repository.get_current_outline(workspace_id)
        if current is None:
            raise OutlineNotFoundError(workspace_id)
        if revision_id != current.id:
            raise InvalidOutlineError("Only the current Report Outline revision can be approved.")
        if current.status == "approved":
            return current
        approved = self._repository.approve_outline(
            outline_id=current.id,
            workspace_id=workspace_id,
            timestamp=self._timestamp(),
        )
        if approved is None or approved.status != "approved":
            raise InvalidOutlineError("The current Report Outline could not be approved.")
        return approved
