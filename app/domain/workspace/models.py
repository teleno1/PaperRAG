from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ReportLanguage = Literal["zh", "en"]
PaperSourceKind = Literal["upload", "discovery"]
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

    def __post_init__(self) -> None:
        self.id = _required(self.id, "paper_id")
        self.workspace_id = _required(self.workspace_id, "workspace_id")
        self.title = _required(self.title, "title")
        self.original_filename = _required(self.original_filename, "original_filename")
        if self.evidence_readiness == "ready" and not self.active_document_version_id:
            raise ValueError("ready paper must have an active document version")

    @property
    def evidence_eligible(self) -> bool:
        return self.selected and self.evidence_readiness == "ready" and bool(self.active_document_version_id)


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
