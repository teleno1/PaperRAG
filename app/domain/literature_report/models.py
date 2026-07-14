from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ReportLanguage = Literal["zh", "en"]
ClaimType = Literal["supported", "evidence_gap"]


def _text(value: Any, field_name: str, *, required: bool = True) -> str:
    normalized = str(value or "").strip()
    if required and not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


@dataclass(slots=True)
class EvidenceCoverage:
    """The ready evidence snapshot used by one report generation attempt."""

    selected_paper_ids: list[str] = field(default_factory=list)
    included_paper_ids: list[str] = field(default_factory=list)
    excluded_papers: list[dict[str, str]] = field(default_factory=list)
    used_ready_subset: bool = False

    def __post_init__(self) -> None:
        self.selected_paper_ids = list(dict.fromkeys(item.strip() for item in self.selected_paper_ids if item.strip()))
        self.included_paper_ids = list(dict.fromkeys(item.strip() for item in self.included_paper_ids if item.strip()))
        self.excluded_papers = [
            {"paper_id": _text(item.get("paper_id"), "excluded_paper_id"), "reason": _text(item.get("reason"), "exclusion_reason")}
            for item in self.excluded_papers
        ]
        if not set(self.included_paper_ids).issubset(self.selected_paper_ids):
            raise ValueError("included evidence must be selected papers")

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_paper_ids": self.selected_paper_ids,
            "included_paper_ids": self.included_paper_ids,
            "excluded_papers": self.excluded_papers,
            "used_ready_subset": self.used_ready_subset,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> EvidenceCoverage:
        payload = payload or {}
        return cls(
            selected_paper_ids=list(payload.get("selected_paper_ids", [])),
            included_paper_ids=list(payload.get("included_paper_ids", [])),
            excluded_papers=list(payload.get("excluded_papers", [])),
            used_ready_subset=bool(payload.get("used_ready_subset", False)),
        )


@dataclass(slots=True)
class SourceChunk:
    """A workspace/version-scoped chunk that may support a Claim Citation."""

    id: str
    workspace_id: str
    paper_id: str
    document_version_id: str
    chunk_id: str
    title: str
    excerpt: str
    section: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    page_start: int | None = None
    page_end: int | None = None
    source_anchor: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.id = _text(self.id, "source_chunk_id")
        self.workspace_id = _text(self.workspace_id, "workspace_id")
        self.paper_id = _text(self.paper_id, "paper_id")
        self.document_version_id = _text(self.document_version_id, "document_version_id")
        self.chunk_id = _text(self.chunk_id, "chunk_id")
        self.title = _text(self.title, "source_title")
        self.excerpt = _text(self.excerpt, "source_excerpt")
        self.section = _text(self.section, "source_section", required=False)
        self.authors = [str(item).strip() for item in self.authors if str(item).strip()]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "paper_id": self.paper_id,
            "document_version_id": self.document_version_id,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "excerpt": self.excerpt,
            "section": self.section,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_anchor": self.source_anchor,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SourceChunk:
        return cls(**payload)


@dataclass(slots=True)
class ClaimCitation:
    """Stable one-to-many link from a Claim to supporting Source Chunks."""

    id: str
    claim_id: str
    source_chunk_ids: list[str] = field(default_factory=list)
    review_state: Literal["verified", "pending_review", "user_confirmed", "evidence_unavailable"] = "verified"

    def __post_init__(self) -> None:
        self.id = _text(self.id, "claim_citation_id")
        self.claim_id = _text(self.claim_id, "claim_id")
        self.source_chunk_ids = list(dict.fromkeys(item.strip() for item in self.source_chunk_ids if item.strip()))
        if not self.source_chunk_ids:
            raise ValueError("claim citation must reference at least one source chunk")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "source_chunk_ids": self.source_chunk_ids,
            "review_state": self.review_state,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ClaimCitation:
        return cls(**payload)


@dataclass(slots=True)
class ReportClaim:
    id: str
    section_id: str
    text: str
    claim_type: ClaimType = "supported"
    citations: list[ClaimCitation] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.id = _text(self.id, "claim_id")
        self.section_id = _text(self.section_id, "section_id")
        self.text = _text(self.text, "claim_text")
        if self.claim_type not in {"supported", "evidence_gap"}:
            raise ValueError("invalid claim type")
        for citation in self.citations:
            if citation.claim_id != self.id:
                raise ValueError("claim citation must belong to its claim")
        if self.claim_type == "supported" and not self.citations:
            raise ValueError("supported claim must have a Claim Citation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "section_id": self.section_id,
            "text": self.text,
            "claim_type": self.claim_type,
            "citations": [citation.to_dict() for citation in self.citations],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReportClaim:
        return cls(
            id=payload["id"],
            section_id=payload["section_id"],
            text=payload["text"],
            claim_type=payload.get("claim_type", "supported"),
            citations=[ClaimCitation.from_dict(item) for item in payload.get("citations", [])],
        )


@dataclass(slots=True)
class LiteratureReportSection:
    id: str
    title: str
    claims: list[ReportClaim] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.id = _text(self.id, "report_section_id")
        self.title = _text(self.title, "report_section_title")
        for claim in self.claims:
            if claim.section_id != self.id:
                raise ValueError("claim must belong to its report section")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "claims": [claim.to_dict() for claim in self.claims]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LiteratureReportSection:
        return cls(
            id=payload["id"],
            title=payload["title"],
            claims=[ReportClaim.from_dict(item) for item in payload.get("claims", [])],
        )


@dataclass(slots=True)
class LiteratureReport:
    id: str
    workspace_id: str
    outline_revision_id: str
    title: str
    language: ReportLanguage
    overview: str
    sections: list[LiteratureReportSection]
    evidence_coverage: EvidenceCoverage
    source_chunks: list[SourceChunk] = field(default_factory=list)
    gap_notes: list[str] = field(default_factory=list)
    status: Literal["ready", "needs_attention"] = "ready"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self.id = _text(self.id, "report_id")
        self.workspace_id = _text(self.workspace_id, "workspace_id")
        self.outline_revision_id = _text(self.outline_revision_id, "outline_revision_id")
        self.title = _text(self.title, "report_title")
        self.overview = _text(self.overview, "report_overview", required=False)
        if self.language not in {"zh", "en"}:
            raise ValueError("report language must be 'zh' or 'en'")
        if not self.sections:
            raise ValueError("report must contain at least one section")
        self.gap_notes = [str(item).strip() for item in self.gap_notes if str(item).strip()]
        if self.gap_notes:
            self.status = "needs_attention"

    @property
    def claims(self) -> list[ReportClaim]:
        return [claim for section in self.sections for claim in section.claims]

    @property
    def citations(self) -> list[ClaimCitation]:
        return [citation for claim in self.claims for citation in claim.citations]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "outline_revision_id": self.outline_revision_id,
            "title": self.title,
            "language": self.language,
            "overview": self.overview,
            "sections": [section.to_dict() for section in self.sections],
            "evidence_coverage": self.evidence_coverage.to_dict(),
            "source_chunks": [chunk.to_dict() for chunk in self.source_chunks],
            "gap_notes": self.gap_notes,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LiteratureReport:
        return cls(
            id=payload["id"],
            workspace_id=payload["workspace_id"],
            outline_revision_id=payload["outline_revision_id"],
            title=payload["title"],
            language=payload.get("language", "zh"),
            overview=payload.get("overview", ""),
            sections=[LiteratureReportSection.from_dict(item) for item in payload.get("sections", [])],
            evidence_coverage=EvidenceCoverage.from_dict(payload.get("evidence_coverage")),
            source_chunks=[SourceChunk.from_dict(item) for item in payload.get("source_chunks", [])],
            gap_notes=list(payload.get("gap_notes", [])),
            status=payload.get("status", "ready"),
            created_at=payload.get("created_at", ""),
            updated_at=payload.get("updated_at", ""),
        )
