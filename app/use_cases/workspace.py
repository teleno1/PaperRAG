from __future__ import annotations

import json
import re
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from app.core.exceptions import (
    InvalidOutlineError,
    InvalidPaperUploadError,
    OutlineNotFoundError,
    OutlineUnavailableError,
    ReportUnavailableError,
    InvalidReportError,
    PaperNotFoundError,
    WorkspaceArchivedError,
    WorkspaceNotFoundError,
    WorkspaceOperationNotFoundError,
)
from app.core.config import get_settings
from app.core.paths import PathManager, get_paths
from app.domain.outline import OutlineSection, ReportOutline
from app.domain.literature_report import EvidenceCoverage, LiteratureReport
from app.domain.workspace import (
    DiscoveryResult,
    ResearchPaper,
    ResearchWorkspace,
    WorkspaceOperation,
)
from app.domain.models.chunk import Chunk, SourceAnchor
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
from app.infrastructure.llm.clients import DashScopeEmbeddingClient
from app.infrastructure.vectorstore.faiss_repository import FaissRepository
from app.infrastructure.vectorstore.index_builder import IndexBuilder, WorkspaceIndexEntry
from app.infrastructure.workspace.repository import WorkspaceRepository
from app.use_cases.workspace_report import (
    GroundedWorkspaceReportGenerator,
    WorkspaceEvidenceRetriever,
    WorkspaceReportGenerator,
    normalize_generated_sections,
)


class UploadPaperResult:
    def __init__(
        self,
        paper: ResearchPaper,
        operation: WorkspaceOperation | None,
        *,
        source_path: Path,
        document_version_id: str,
        download_url: str | None = None,
        download_urls: list[str] | None = None,
    ) -> None:
        self.paper = paper
        self.operation = operation
        self.source_path = source_path
        self.document_version_id = document_version_id
        self.download_urls = list(dict.fromkeys(download_urls or ([download_url] if download_url else [])))
        self.download_url = self.download_urls[0] if self.download_urls else None
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
        report_generator: WorkspaceReportGenerator | None = None,
        evidence_retriever: WorkspaceEvidenceRetriever | None = None,
        embedding_client: DashScopeEmbeddingClient | None = None,
    ) -> None:
        self._repository = repository
        self._storage_root = storage_root
        self._parser_registry = parser_registry or ParserRegistry([MinerUParser()])
        self._chunk_builder = chunk_builder or ChunkBuilder()
        self._discovery_providers = dict(discovery_providers or {"openalex": OpenAlexProvider()})
        self._pdf_downloader = pdf_downloader or RequestsPdfDownloader()
        self._report_generator = report_generator or GroundedWorkspaceReportGenerator()
        # Direct construction remains a deterministic compatibility seam for the
        # pre-05A tests. Production construction through from_paths always
        # supplies the real provider client; it never substitutes local vectors.
        self._embedding_client = embedding_client
        self._evidence_retriever = evidence_retriever or WorkspaceEvidenceRetriever(
            repository=repository,
            storage_root=storage_root,
            embedding_client=embedding_client,
        )
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
            embedding_client=DashScopeEmbeddingClient(settings),
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
                candidates=[
                    paper
                    for paper in workspace.papers
                    if paper.source_kind == "discovery" and not paper.dismissed
                ],
                page=page,
                per_page=per_page,
                error_message=str(exc),
                retryable=exc.retryable,
                retry_after_seconds=exc.retry_after_seconds,
                next_action=exc.next_action,
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
            if paper.dismissed:
                continue
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
            retry_after_seconds=getattr(result, "retry_after_seconds", None),
            next_action=getattr(result, "next_action", None),
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

    @staticmethod
    def _clean_chunk_excerpt(chunk: Chunk) -> str:
        if chunk.excerpt.strip():
            return chunk.excerpt.strip()
        content = chunk.content.strip()
        lines = content.splitlines()
        if len(lines) >= 3 and lines[0].startswith("[Title:") and lines[1].startswith("[Section:"):
            return " ".join(lines[2:]).strip()
        return content

    def _ensure_chunk_anchors(
        self,
        *,
        chunks: list[Chunk],
        document_version_id: str,
        source_path: Path,
        parser: str,
        parser_version: str | None = None,
    ) -> list[Chunk]:
        for chunk in chunks:
            if chunk.source_anchor is None:
                excerpt = self._clean_chunk_excerpt(chunk)
                chunk.excerpt = excerpt
                chunk.source_anchor = SourceAnchor(
                    document_version_id=document_version_id,
                    source_path=str(source_path),
                    section=chunk.section,
                    excerpt=excerpt,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    character_start=chunk.character_start,
                    character_end=chunk.character_end,
                    parser=parser,
                    parser_version=parser_version,
                )
            else:
                chunk.excerpt = chunk.source_anchor.excerpt
                chunk.page_start = chunk.source_anchor.page_start
                chunk.page_end = chunk.source_anchor.page_end
                chunk.character_start = chunk.source_anchor.character_start
                chunk.character_end = chunk.source_anchor.character_end
        return chunks

    @staticmethod
    def _serialize_chunk(chunk: Chunk, *, chunk_id: str, document_version_id: str) -> dict:
        return {
            "chunk_id": chunk_id,
            "document_version_id": document_version_id,
            "section": chunk.section,
            "content": chunk.content,
            "excerpt": chunk.excerpt,
            "title": chunk.title,
            "authors": chunk.authors,
            "year": chunk.year,
            "venue": chunk.venue,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "character_start": chunk.character_start,
            "character_end": chunk.character_end,
            "source_anchor": chunk.source_anchor.to_dict() if chunk.source_anchor else None,
        }

    def _load_workspace_chunks(self, paper: ResearchPaper) -> list[Chunk]:
        storage_path = self._repository.get_paper_storage_path(
            workspace_id=paper.workspace_id,
            paper_id=paper.id,
        )
        if not storage_path or not paper.active_document_version_id:
            return []
        safe_storage_path = Path(storage_path).resolve()
        try:
            safe_storage_path.relative_to(self._storage_root.resolve())
        except ValueError:
            return []
        chunks_path = safe_storage_path.parent / "chunks.json"
        if not chunks_path.is_file():
            return []
        raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        chunks: list[Chunk] = []
        for raw in raw_chunks if isinstance(raw_chunks, list) else []:
            if not isinstance(raw, dict):
                continue
            if str(raw.get("document_version_id") or "") != paper.active_document_version_id:
                continue
            anchor_payload = raw.get("source_anchor")
            anchor = SourceAnchor.from_dict(anchor_payload) if isinstance(anchor_payload, dict) else None
            if anchor is not None and anchor.document_version_id != paper.active_document_version_id:
                raise ValueError("chunk anchor belongs to a different document version")
            chunk = Chunk(
                content=str(raw.get("content") or "").strip(),
                excerpt=str(raw.get("excerpt") or "").strip(),
                section=str(raw.get("section") or "UNKNOWN"),
                title=str(raw.get("title") or paper.title),
                authors=list(raw.get("authors") or paper.authors),
                year=str(raw.get("year") or paper.year),
                venue=str(raw.get("venue") or paper.venue),
                page_start=raw.get("page_start"),
                page_end=raw.get("page_end"),
                character_start=raw.get("character_start"),
                character_end=raw.get("character_end"),
                source_anchor=anchor,
            )
            chunks.append(
                self._ensure_chunk_anchors(
                    chunks=[chunk],
                    document_version_id=paper.active_document_version_id,
                    source_path=safe_storage_path,
                    parser="workspace-artifact",
                )[0]
            )
        return chunks

    def _workspace_index_entries(
        self,
        workspace_id: str,
        *,
        pending_paper: ResearchPaper | None = None,
        pending_chunks: list[Chunk] | None = None,
        pending_source_path: Path | None = None,
        pending_document_version_id: str | None = None,
    ) -> list[WorkspaceIndexEntry]:
        workspace = self.get_workspace(workspace_id)
        entries: list[WorkspaceIndexEntry] = []
        for paper in workspace.papers:
            if pending_paper is not None and paper.id == pending_paper.id:
                continue
            if not paper.evidence_eligible:
                continue
            storage_path = self._repository.get_paper_storage_path(
                workspace_id=workspace_id,
                paper_id=paper.id,
            )
            chunks = self._load_workspace_chunks(paper)
            if not storage_path or not chunks or not paper.active_document_version_id:
                raise ValueError("ready paper is missing its indexed chunk artifact")
            entries.append(
                WorkspaceIndexEntry(
                    workspace_id=workspace_id,
                    paper_id=paper.id,
                    document_version_id=paper.active_document_version_id,
                    source_path=storage_path,
                    chunks=chunks,
                )
            )
        if pending_paper is not None and pending_chunks:
            if not pending_source_path or not pending_document_version_id:
                raise ValueError("pending index entry is missing its document version")
            entries.append(
                WorkspaceIndexEntry(
                    workspace_id=workspace_id,
                    paper_id=pending_paper.id,
                    document_version_id=pending_document_version_id,
                    source_path=str(pending_source_path),
                    chunks=pending_chunks,
                )
            )
        return entries

    def _rebuild_workspace_index(
        self,
        workspace_id: str,
        *,
        pending_paper: ResearchPaper | None = None,
        pending_chunks: list[Chunk] | None = None,
        pending_source_path: Path | None = None,
        pending_document_version_id: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> int:
        if self._embedding_client is None:
            return 0
        entries = self._workspace_index_entries(
            workspace_id,
            pending_paper=pending_paper,
            pending_chunks=pending_chunks,
            pending_source_path=pending_source_path,
            pending_document_version_id=pending_document_version_id,
        )
        repository = FaissRepository(
            index_path=self._storage_root / workspace_id / "index" / "evidence.faiss",
            metadata_path=self._storage_root / workspace_id / "index" / "metadata.json",
            embed_dim=get_settings().models.embedding_dimension or 1024,
        )
        if not entries:
            repository.clear()
            return 0
        index_builder = IndexBuilder(
            embedding_client=self._embedding_client,
            expected_embedding_dimension=get_settings().models.embedding_dimension,
        )
        total_work = sum(len(entry.chunks) for entry in entries)
        if progress_callback is not None:
            progress_callback(0, total_work)
        vectors, metadata = index_builder.build_workspace(
            entries,
            progress_callback=(
                (lambda completed: progress_callback(completed, total_work))
                if progress_callback is not None
                else None
            ),
        )
        if not vectors or len(vectors) != len(metadata):
            raise ValueError("workspace evidence index contains no complete vectors")
        repository.save(vectors, metadata)
        return len(metadata)

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
            if result.download_urls:
                errors: list[PdfDownloadError] = []
                downloaded = False
                for download_url in result.download_urls:
                    try:
                        result.download_result = self._pdf_downloader.download(download_url, source_path)
                        downloaded = True
                        break
                    except PdfDownloadError as exc:
                        errors.append(exc)
                if not downloaded:
                    last_error = errors[-1] if errors else PdfDownloadError(
                        "download_failed", "No public PDF source was available."
                    )
                    raise PdfDownloadError(
                        last_error.category,
                        f"All public PDF sources failed: {last_error}",
                    ) from last_error
            current_phase = "parsing"
            self._repository.mark_paper_processing_phase(
                workspace_id=workspace_id,
                paper_id=paper_id,
                document_version_id=document_version_id,
                phase=current_phase,
                timestamp=self._timestamp(),
            )
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
            self._repository.mark_paper_processing_phase(
                workspace_id=workspace_id,
                paper_id=paper_id,
                document_version_id=document_version_id,
                phase=current_phase,
                timestamp=self._timestamp(),
            )
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
            chunks = self._ensure_chunk_anchors(
                chunks=chunks,
                document_version_id=document_version_id,
                source_path=source_path,
                parser=str(parsed.metadata.get("parser") or parsed.source_type),
                parser_version=(
                    str(parsed.metadata["parser_version"])
                    if parsed.metadata.get("parser_version") is not None
                    else None
                ),
            )
            (version_artifact_dir / "chunks.json").write_text(
                json.dumps(
                    [
                        self._serialize_chunk(
                            chunk,
                            chunk_id=f"{document_version_id}__chunk_{index:04d}",
                            document_version_id=document_version_id,
                        )
                        for index, chunk in enumerate(chunks)
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._repository.update_operation(
                operation_id=operation.id,
                status="running",
                phase=current_phase,
                timestamp=self._timestamp(),
                completed_work=0,
                total_work=len(chunks),
                retry_action=None,
            )
            indexed_work = self._rebuild_workspace_index(
                workspace_id,
                pending_paper=paper,
                pending_chunks=chunks,
                pending_source_path=source_path,
                pending_document_version_id=document_version_id,
                progress_callback=(
                    lambda completed, total: self._repository.update_operation(
                        operation_id=operation.id,
                        status="running",
                        phase=current_phase,
                        timestamp=self._timestamp(),
                        completed_work=completed,
                        total_work=total,
                        retry_action=None,
                    )
                ),
            )
            self._repository.update_operation(
                operation_id=operation.id,
                status="running",
                phase=current_phase,
                timestamp=self._timestamp(),
                completed_work=indexed_work or len(chunks),
                total_work=indexed_work or len(chunks),
                retry_action=None,
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
                completed_work=indexed_work or len(chunks),
                total_work=indexed_work or len(chunks),
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
            if current_phase == "indexing" and self._embedding_client is not None:
                safe_message = "Evidence indexing failed. Check the embedding provider configuration or availability, then retry."
                error_category = "evidence_indexing_failed"
            elif current_phase == "parsing":
                safe_message = "PDF parsing failed. Retry the import or provide another authorised PDF."
                error_category = "paper_parsing_failed"
            else:
                safe_message = "Paper import failed. Retry the import or provide another authorised PDF."
                error_category = "paper_import_failed"
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
                error_category=error_category,
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
        can_auto_import = paper.pdf_urls and (paper.is_open_access is True or paper.provider == "arxiv")
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
            download_urls=paper.pdf_urls,
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
            download_urls=paper.pdf_urls if paper.source_kind == "discovery" else None,
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
        if self._embedding_client is not None:
            try:
                self._rebuild_workspace_index(workspace_id)
            except Exception as exc:
                # Keep the selection boundary and the physical index aligned.
                self._repository.set_paper_selected(
                    workspace_id=workspace_id,
                    paper_id=paper_id,
                    selected=paper.selected,
                    timestamp=self._timestamp(),
                )
                raise InvalidPaperUploadError(
                    "The workspace evidence index could not be updated. Retry after checking the embedding provider."
                ) from exc
        return updated

    def remove_paper(self, workspace_id: str, paper_id: str) -> ResearchPaper:
        return self._set_paper_selection(workspace_id, paper_id, selected=False)

    def select_paper(self, workspace_id: str, paper_id: str) -> ResearchPaper:
        return self._set_paper_selection(workspace_id, paper_id, selected=True)

    def dismiss_paper(self, workspace_id: str, paper_id: str) -> ResearchPaper:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        paper = next((item for item in workspace.papers if item.id == paper_id), None)
        if paper is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        if paper.source_kind != "discovery" or paper.selected:
            raise InvalidPaperUploadError("Only an unselected Candidate Paper can be dismissed.")
        updated = self._repository.set_paper_dismissed(
            workspace_id=workspace_id,
            paper_id=paper_id,
            dismissed=True,
            timestamp=self._timestamp(),
        )
        if updated is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        return updated

    def restore_dismissed_paper(self, workspace_id: str, paper_id: str) -> ResearchPaper:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        paper = next((item for item in workspace.papers if item.id == paper_id), None)
        if paper is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        if paper.source_kind != "discovery" or paper.selected:
            raise InvalidPaperUploadError("Only an unselected Candidate Paper can be restored.")
        updated = self._repository.set_paper_dismissed(
            workspace_id=workspace_id,
            paper_id=paper_id,
            dismissed=False,
            timestamp=self._timestamp(),
        )
        if updated is None:
            raise PaperNotFoundError(workspace_id, paper_id)
        return updated

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
        if operation.operation_type not in {"generate_outline", "generate_report"}:
            raise InvalidOutlineError("Only failed Report Outline or Literature Report operations can be retried here.")
        if operation.status not in {"failed", "interrupted"}:
            raise InvalidOutlineError("Only failed or interrupted workspace report operations can be retried.")
        if operation.operation_type == "generate_outline":
            retry = self.start_outline_generation(operation.workspace_id)
            self.enqueue_outline_generation(retry)
        else:
            retry = self.start_report_generation(
                operation.workspace_id,
                use_ready_subset=bool((operation.input_snapshot or {}).get("used_ready_subset", False)),
            )
            self.enqueue_report_generation(retry)
        return retry

    def get_report_draft(self, workspace_id: str) -> LiteratureReport | None:
        self.get_workspace(workspace_id)
        return self._repository.get_report_draft(workspace_id)

    def _report_evidence_snapshot(
        self,
        workspace: ResearchWorkspace,
        *,
        use_ready_subset: bool,
    ) -> EvidenceCoverage:
        selected = [paper for paper in workspace.papers if paper.selected]
        included = [paper for paper in selected if paper.evidence_eligible]
        excluded = [
            {"paper_id": paper.id, "reason": paper.evidence_readiness}
            for paper in selected
            if not paper.evidence_eligible
        ]
        if not included:
            raise ReportUnavailableError(
                "A Literature Report needs at least one ready Selected Paper.",
                "select and process at least one Selected Paper until Evidence Readiness is ready",
            )
        if excluded and not use_ready_subset:
            raise ReportUnavailableError(
                "Generation has mixed readiness; confirm the ready subset before generating.",
                "confirm_ready_subset",
            )
        return EvidenceCoverage(
            selected_paper_ids=[paper.id for paper in selected],
            included_paper_ids=[paper.id for paper in included],
            excluded_papers=excluded,
            used_ready_subset=bool(excluded),
        )

    def start_report_generation(
        self,
        workspace_id: str,
        *,
        use_ready_subset: bool = False,
    ) -> WorkspaceOperation:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        outline = self._repository.get_current_outline(workspace_id)
        if outline is None:
            raise ReportUnavailableError(
                "A Literature Report requires a current Report Outline.",
                "generate and approve a Report Outline",
            )
        if outline.status != "approved":
            raise ReportUnavailableError(
                "A Literature Report can only be generated from an approved Report Outline.",
                "approve the current Report Outline",
            )
        coverage = self._report_evidence_snapshot(workspace, use_ready_subset=use_ready_subset)
        snapshot = {
            "outline_revision_id": outline.id,
            "selected_paper_ids": coverage.selected_paper_ids,
            "included_paper_ids": coverage.included_paper_ids,
            "excluded_papers": coverage.excluded_papers,
            "used_ready_subset": coverage.used_ready_subset,
        }
        return self._repository.create_operation(
            operation_id=uuid.uuid4().hex,
            workspace_id=workspace_id,
            paper_id=None,
            operation_type="generate_report",
            phase="generating",
            timestamp=self._timestamp(),
            input_snapshot=snapshot,
        )

    def enqueue_report_generation(self, operation: WorkspaceOperation) -> None:
        self._executor.submit(self.process_report_generation, operation.id, operation.workspace_id)

    def process_report_generation(self, operation_id: str, workspace_id: str) -> LiteratureReport:
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
            snapshot = operation.input_snapshot or {}
            outline_id = str(snapshot.get("outline_revision_id") or "")
            outline = self._repository.get_outline_revision(workspace_id, outline_id)
            if outline is None or outline.status != "approved":
                raise ReportUnavailableError("The approved Report Outline used by this operation is no longer available.", "approve a current Report Outline")
            included_ids = list(snapshot.get("included_paper_ids", []))
            papers = [
                paper
                for paper in workspace.papers
                if paper.id in included_ids and paper.evidence_eligible
            ]
            if len(papers) != len(included_ids):
                raise ReportUnavailableError(
                    "The ready evidence snapshot changed before report generation completed.",
                    "review paper readiness and retry report generation",
                )
            coverage = EvidenceCoverage(
                selected_paper_ids=list(snapshot.get("selected_paper_ids", [])),
                included_paper_ids=included_ids,
                excluded_papers=list(snapshot.get("excluded_papers", [])),
                used_ready_subset=bool(snapshot.get("used_ready_subset", False)),
            )
            query = " ".join(
                [
                    workspace.topic,
                    outline.research_question,
                    *(f"{section.title} {section.description}" for section in outline.sections),
                ]
            )
            sources = self._evidence_retriever.search(papers=papers, query=query, top_k=24)
            raw_payload = self._report_generator.generate(
                topic=workspace.topic,
                report_language=workspace.report_language,
                outline=outline,
                sources=sources,
            )
            if not isinstance(raw_payload, dict):
                raise ValueError("report generator returned a non-object payload")
            sections, gap_notes = normalize_generated_sections(
                raw_payload=raw_payload,
                outline=outline,
                allowed_sources=sources,
                report_language=workspace.report_language,
            )
            now = self._timestamp()
            report = LiteratureReport(
                id=uuid.uuid4().hex,
                workspace_id=workspace_id,
                outline_revision_id=outline.id,
                title=str(raw_payload.get("title") or outline.title),
                language=workspace.report_language,
                overview=str(raw_payload.get("overview") or outline.research_question),
                sections=sections,
                evidence_coverage=coverage,
                source_chunks=sources,
                gap_notes=gap_notes,
                created_at=now,
                updated_at=now,
            )
            saved = self._repository.save_report_draft(report=report, timestamp=now)
            self._repository.update_operation(
                operation_id=operation.id,
                status="succeeded",
                phase="draft_ready",
                timestamp=self._timestamp(),
                completed_work=1,
                total_work=1,
                retry_action=None,
            )
            return saved
        except Exception as exc:
            self._repository.update_operation(
                operation_id=operation.id,
                status="failed",
                phase="generating",
                timestamp=self._timestamp(),
                error_category="report_generation_failed",
                error_message="Literature Report generation failed. Retry after checking the approved outline and ready evidence.",
                retry_action="retry",
            )
            if isinstance(exc, ReportUnavailableError):
                raise
            raise ReportUnavailableError(
                "Literature Report generation failed. Retry after checking the approved outline and ready evidence.",
                "retry_report_generation",
            ) from exc

    def generate_report(
        self,
        workspace_id: str,
        *,
        use_ready_subset: bool = False,
    ) -> LiteratureReport:
        operation = self.start_report_generation(workspace_id, use_ready_subset=use_ready_subset)
        return self.process_report_generation(operation.id, workspace_id)

    def save_report_draft(self, workspace_id: str, report: LiteratureReport) -> LiteratureReport:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        current = self._repository.get_report_draft(workspace_id)
        if current is None:
            raise ReportUnavailableError("There is no generated Literature Report draft to edit.", "generate a Literature Report")
        if report.workspace_id != workspace_id or report.id != current.id:
            raise InvalidReportError("Only the current workspace Literature Report draft can be edited.")
        report.source_chunks = current.source_chunks
        report.evidence_coverage = current.evidence_coverage
        report.outline_revision_id = current.outline_revision_id
        allowed_source_ids = {source.id for source in current.source_chunks}
        submitted_source_ids = {
            source_id
            for citation in report.citations
            for source_id in citation.source_chunk_ids
        }
        if not submitted_source_ids.issubset(allowed_source_ids):
            raise InvalidReportError("Claim Citations must reference Source Chunks from this report's evidence snapshot.")
        report.created_at = current.created_at
        report.updated_at = self._timestamp()
        return self._repository.save_report_draft(report=report, timestamp=report.updated_at)

    def get_outline(self, workspace_id: str) -> ReportOutline | None:
        self.get_workspace(workspace_id)
        return self._repository.get_current_outline(workspace_id)

    def list_outline_revisions(self, workspace_id: str) -> list[ReportOutline]:
        self.get_workspace(workspace_id)
        return self._repository.list_outline_revisions(workspace_id)

    def restore_outline_revision(self, workspace_id: str, revision_id: str) -> ReportOutline:
        workspace = self.get_workspace(workspace_id)
        if workspace.state == "archived":
            raise WorkspaceArchivedError(workspace_id)
        source = self._repository.get_outline_revision(workspace_id, revision_id)
        if source is None:
            raise OutlineNotFoundError(workspace_id)
        return self._repository.create_outline_revision(
            outline_id=uuid.uuid4().hex,
            workspace_id=workspace_id,
            status="draft",
            title=source.title,
            research_question=source.research_question,
            sections=source.sections,
            evidence_paper_ids=source.evidence_paper_ids,
            timestamp=self._timestamp(),
        )

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
                OutlineSection("methods-findings", "方法与主要发现", "概括已选论文支持的方法、数据和主要发现。"),
                OutlineSection("comparison", "研究比较", "比较不同研究的假设、数据、方法和结论。"),
                OutlineSection("limitations-gaps", "局限与研究缺口", "指出当前证据能够支持的范围、局限和仍待回答的问题。"),
                OutlineSection("conclusion", "结论", "在不添加无依据事实的前提下回答研究问题并综合主要结论。"),
                OutlineSection("references", "参考文献", "列出本次批准大纲所使用的已选论文。"),
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
