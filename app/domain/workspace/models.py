from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

ReportLanguage = Literal["zh", "en"]
PaperSourceKind = Literal["upload", "discovery"]
DiscoveryStatus = Literal["succeeded", "empty", "retryable_error", "failed"]
EvidenceReadiness = Literal[
    "awaiting_authorised_file",
    "importing",
    "parsing",
    "indexing",
    "ready",
    "failed",
    "unavailable",
]
WorkspaceOperationStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "failed",
    "interrupted",
    "cancelled",
]


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    return normalized or None


@dataclass(slots=True)
class DiscoveryCandidate:
    provider: str
    provider_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    year: str = ""
    published_at: str | None = None
    source_updated_at: str | None = None
    venue: str = ""
    doi: str | None = None
    arxiv_id: str | None = None
    source_url: str | None = None
    pdf_url: str | None = None
    is_open_access: bool | None = None
    license: str | None = None
    source_links: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.provider = _required(self.provider, "provider")
        self.provider_id = _required(self.provider_id, "provider_id")
        self.title = _required(self.title, "title")
        self.doi = normalize_doi(self.doi)
        self.arxiv_id = re.sub(r"v\d+$", "", self.arxiv_id.strip()) if self.arxiv_id else None
        links = [link.strip() for link in self.source_links if link and link.strip()]
        for link in (self.source_url, self.pdf_url):
            if link and link.strip() and link.strip() not in links:
                links.append(link.strip())
        self.source_links = links


@dataclass(slots=True)
class DiscoveryPage:
    provider: str
    query: str
    candidates: list[DiscoveryCandidate] = field(default_factory=list)
    page: int = 1
    per_page: int = 10
    total_count: int | None = None
    next_page: int | None = None


@dataclass(slots=True)
class DiscoveryResult:
    status: DiscoveryStatus
    provider: str
    query: str
    candidates: list[ResearchPaper] = field(default_factory=list)
    page: int = 1
    per_page: int = 10
    total_count: int | None = None
    next_page: int | None = None
    error_message: str | None = None
    retryable: bool = False


@dataclass(slots=True)
class DocumentVersion:
    id: str
    workspace_id: str
    paper_id: str
    source_path: str
    status: EvidenceReadiness
    parsed_artifact_path: str | None = None
    failure_phase: str | None = None
    failure_message: str | None = None
    requested_source_url: str | None = None
    final_source_url: str | None = None
    content_sha256: str | None = None
    imported_at: str | None = None

    def __post_init__(self) -> None:
        self.id = _required(self.id, "document_version_id")
        self.workspace_id = _required(self.workspace_id, "workspace_id")
        self.paper_id = _required(self.paper_id, "paper_id")
        self.source_path = _required(self.source_path, "source_path")


@dataclass(slots=True)
class ResearchPaper:
    id: str
    workspace_id: str
    title: str
    source_kind: PaperSourceKind
    original_filename: str
    selected: bool
    evidence_readiness: EvidenceReadiness
    active_document_version_id: str | None = None
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    failure_phase: str | None = None
    failure_message: str | None = None
    retryable: bool = False
    provider: str | None = None
    provider_id: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    abstract: str = ""
    source_url: str | None = None
    pdf_url: str | None = None
    is_open_access: bool | None = None
    license: str | None = None
    source_links: list[str] = field(default_factory=list)
    discovery_query: str | None = None
    discovered_at: str | None = None
    published_at: str | None = None
    source_updated_at: str | None = None

    def __post_init__(self) -> None:
        self.id = _required(self.id, "paper_id")
        self.workspace_id = _required(self.workspace_id, "workspace_id")
        self.title = _required(self.title, "title")
        self.original_filename = _required(self.original_filename, "original_filename")
        self.doi = normalize_doi(self.doi)
        if self.provider:
            self.provider = self.provider.strip() or None
        if self.provider_id:
            self.provider_id = self.provider_id.strip() or None
        if self.arxiv_id:
            self.arxiv_id = re.sub(r"v\d+$", "", self.arxiv_id.strip()) or None
        self.source_links = [link.strip() for link in self.source_links if link and link.strip()]
        if self.evidence_readiness == "ready" and not self.active_document_version_id:
            raise ValueError("ready paper must have an active document version")

    @property
    def evidence_eligible(self) -> bool:
        return self.selected and self.evidence_readiness == "ready" and bool(self.active_document_version_id)

    @property
    def next_action(self) -> str | None:
        if not self.selected:
            return "select"
        if self.evidence_readiness == "unavailable":
            can_auto_import = self.pdf_url and (self.is_open_access is True or self.provider == "arxiv")
            return "import_pdf" if can_auto_import else "upload_authorised_pdf"
        if self.evidence_readiness == "awaiting_authorised_file":
            return "upload_authorised_pdf"
        if self.evidence_readiness == "failed" and self.retryable:
            return "retry_import"
        return None


@dataclass(slots=True)
class ResearchWorkspace:
    id: str
    topic: str
    report_language: ReportLanguage
    state: Literal["setup", "active", "archived"] = "setup"
    created_at: str = ""
    updated_at: str = ""
    papers: list[ResearchPaper] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.id = _required(self.id, "workspace_id")
        self.topic = _required(self.topic, "topic")
        if self.report_language not in {"zh", "en"}:
            raise ValueError("report_language must be 'zh' or 'en'")
        if self.state not in {"setup", "active", "archived"}:
            raise ValueError("invalid workspace state")


@dataclass(slots=True)
class WorkspaceOperation:
    id: str
    workspace_id: str
    operation_type: str
    status: WorkspaceOperationStatus
    phase: str
    paper_id: str | None = None
    error_category: str | None = None
    error_message: str | None = None
    retry_action: str | None = None
    completed_work: int = 0
    total_work: int = 1
    started_at: str | None = None
    finished_at: str | None = None

    def __post_init__(self) -> None:
        self.id = _required(self.id, "operation_id")
        self.workspace_id = _required(self.workspace_id, "workspace_id")
        self.operation_type = _required(self.operation_type, "operation_type")
        self.phase = _required(self.phase, "phase")
