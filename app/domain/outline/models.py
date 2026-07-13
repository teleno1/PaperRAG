from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.domain.review.models import OutlineNode

OutlineStatus = Literal["draft", "approved"]


@dataclass(slots=True)
class OutlineSection:
    """One editable section in a workspace Report Outline."""

    id: str
    title: str
    description: str = ""

    def __post_init__(self) -> None:
        self.id = self.id.strip()
        self.title = self.title.strip()
        self.description = self.description.strip()
        if not self.id:
            raise ValueError("outline section id must not be empty")
        if not self.title:
            raise ValueError("outline section title must not be empty")


@dataclass(slots=True)
class ReportOutline:
    """The current or historical revision of a workspace Report Outline."""

    id: str
    workspace_id: str
    revision_number: int
    status: OutlineStatus
    title: str
    research_question: str
    sections: list[OutlineSection] = field(default_factory=list)
    evidence_paper_ids: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    approved_at: str | None = None

    def __post_init__(self) -> None:
        self.id = self.id.strip()
        self.workspace_id = self.workspace_id.strip()
        self.title = self.title.strip()
        self.research_question = self.research_question.strip()
        if not self.id or not self.workspace_id:
            raise ValueError("outline identity must not be empty")
        if self.revision_number < 1:
            raise ValueError("outline revision_number must be positive")
        if self.status not in {"draft", "approved"}:
            raise ValueError("outline status must be 'draft' or 'approved'")
        if not self.title:
            raise ValueError("outline title must not be empty")
        if not self.research_question:
            raise ValueError("outline research_question must not be empty")
        if not self.sections:
            raise ValueError("outline must contain at least one section")
        ids = [section.id for section in self.sections]
        if len(ids) != len(set(ids)):
            raise ValueError("outline section ids must be unique")
        self.evidence_paper_ids = list(dict.fromkeys(item.strip() for item in self.evidence_paper_ids if item.strip()))


__all__ = ["OutlineNode", "OutlineSection", "OutlineStatus", "ReportOutline"]

