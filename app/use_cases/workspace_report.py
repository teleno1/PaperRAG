from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Protocol

from app.domain.literature_report import (
    ClaimCitation,
    LiteratureReportSection,
    ReportClaim,
    SourceChunk,
)
from app.domain.outline import ReportOutline
from app.domain.workspace import ResearchPaper


class WorkspaceReportGenerator(Protocol):
    def generate(
        self,
        *,
        topic: str,
        report_language: str,
        outline: ReportOutline,
        sources: list[SourceChunk],
    ) -> dict:
        """Return a structured, source-id-citing report payload."""


class WorkspaceEvidenceRetriever:
    """Read only the active version chunks belonging to ready selected papers."""

    def __init__(self, *, repository, storage_root: Path) -> None:
        self._repository = repository
        self._storage_root = storage_root

    @staticmethod
    def _tokens(text: str) -> set[str]:
        words = set(re.findall(r"[a-z0-9]{2,}", text.lower()))
        words.update(char for char in text if "\u4e00" <= char <= "\u9fff")
        return words

    def _load_paper_chunks(self, paper: ResearchPaper) -> list[SourceChunk]:
        storage_path = self._repository.get_paper_storage_path(
            workspace_id=paper.workspace_id,
            paper_id=paper.id,
        )
        if not storage_path or not paper.active_document_version_id:
            return []
        try:
            safe_storage_path = Path(storage_path).resolve()
            safe_storage_path.relative_to(self._storage_root.resolve())
        except ValueError:
            return []
        chunks_path = safe_storage_path.parent / "chunks.json"
        if not chunks_path.is_file():
            return []
        try:
            raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        sources: list[SourceChunk] = []
        for raw in raw_chunks if isinstance(raw_chunks, list) else []:
            if not isinstance(raw, dict):
                continue
            chunk_id = str(raw.get("chunk_id") or "").strip()
            document_version_id = str(raw.get("document_version_id") or "").strip()
            content = str(raw.get("content") or "").strip()
            if not chunk_id or not content or document_version_id != paper.active_document_version_id:
                continue
            sources.append(
                SourceChunk(
                    id=chunk_id,
                    workspace_id=paper.workspace_id,
                    paper_id=paper.id,
                    document_version_id=document_version_id,
                    chunk_id=chunk_id,
                    title=str(raw.get("title") or paper.title),
                    excerpt=content[:1600],
                    section=str(raw.get("section") or ""),
                    authors=list(raw.get("authors") or paper.authors),
                    year=str(raw.get("year") or paper.year),
                    venue=str(raw.get("venue") or paper.venue),
                )
            )
        return sources

    def search(self, *, papers: list[ResearchPaper], query: str, top_k: int = 16) -> list[SourceChunk]:
        query_tokens = self._tokens(query)
        scored: list[tuple[int, int, SourceChunk]] = []
        order = 0
        for paper in papers:
            for source in self._load_paper_chunks(paper):
                order += 1
                haystack = f"{source.title} {source.section} {source.excerpt}".lower()
                score = sum(1 for token in query_tokens if token.lower() in haystack)
                if not query_tokens or score:
                    scored.append((score, -order, source))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in scored[: max(top_k, 1)]]


class GroundedWorkspaceReportGenerator:
    """Offline-safe generator used by the workspace seam and acceptance tests.

    It turns retrieved excerpts into editable, explicitly cited draft claims. A
    deployment may replace it with an LLM-backed collaborator without changing
    the workspace persistence or API contract.
    """

    def generate(
        self,
        *,
        topic: str,
        report_language: str,
        outline: ReportOutline,
        sources: list[SourceChunk],
    ) -> dict:
        sections: list[dict] = []
        for section in outline.sections:
            section_sources = sources[:2]
            if section_sources:
                first = section_sources[0]
                if report_language == "zh":
                    text = f"围绕“{section.title}”，已选论文提供的可追溯证据摘要：{first.excerpt}"
                else:
                    text = f"For {section.title}, the selected papers provide this traceable evidence summary: {first.excerpt}"
                sections.append(
                    {
                        "id": section.id,
                        "title": section.title,
                        "claims": [
                            {
                                "text": text,
                                "cited_source_ids": [source.id for source in section_sources],
                            }
                        ],
                    }
                )
            else:
                gap = (
                    f"本次已选证据未能支持“{section.title}”；需要补充或处理更多论文。"
                    if report_language == "zh"
                    else f"The selected evidence does not support “{section.title}”; more processed papers are needed."
                )
                sections.append({"id": section.id, "title": section.title, "claims": [{"text": gap, "claim_type": "evidence_gap"}]})
        return {
            "title": outline.title or topic,
            "overview": outline.research_question,
            "sections": sections,
        }


def new_claim_id() -> str:
    return f"claim-{uuid.uuid4().hex}"


def new_citation_id() -> str:
    return f"citation-{uuid.uuid4().hex}"


def normalize_generated_sections(
    *,
    raw_payload: dict,
    outline: ReportOutline,
    allowed_sources: list[SourceChunk],
    report_language: str,
) -> tuple[list[LiteratureReportSection], list[str]]:
    allowed_by_id = {source.id: source for source in allowed_sources}
    raw_sections = raw_payload.get("sections", []) if isinstance(raw_payload, dict) else []
    sections_by_id = {
        str(item.get("id") or item.get("section_id") or "").strip(): item
        for item in raw_sections
        if isinstance(item, dict)
    }
    normalized: list[LiteratureReportSection] = []
    gap_notes: list[str] = []
    for outline_section in outline.sections:
        raw_section = sections_by_id.get(outline_section.id)
        if raw_section is None:
            raw_section = next(
                (item for item in raw_sections if isinstance(item, dict) and item.get("title") == outline_section.title),
                None,
            )
        raw_claims = raw_section.get("claims", []) if isinstance(raw_section, dict) else []
        if not raw_claims and isinstance(raw_section, dict):
            raw_claims = [raw_section]
        claims: list[ReportClaim] = []
        for raw_claim in raw_claims:
            if not isinstance(raw_claim, dict):
                continue
            text = str(raw_claim.get("text") or raw_claim.get("body") or "").strip()
            if not text:
                continue
            claim_type = "evidence_gap" if raw_claim.get("claim_type") == "evidence_gap" else "supported"
            cited_ids = raw_claim.get("cited_source_ids") or raw_claim.get("source_ids") or raw_claim.get("citations") or []
            if not isinstance(cited_ids, list):
                cited_ids = []
            valid_ids = list(dict.fromkeys(str(item).strip() for item in cited_ids if str(item).strip() in allowed_by_id))
            if claim_type == "supported" and not valid_ids:
                claim_type = "evidence_gap"
                text = (
                    f"本次已选证据未能验证“{outline_section.title}”中的这条内容。"
                    if report_language == "zh"
                    else f"The selected evidence could not verify this content in “{outline_section.title}”."
                )
                gap_notes.append(f"{outline_section.title}: generated text had no validated source support.")
            claim_id = str(raw_claim.get("id") or "").strip() or new_claim_id()
            citations = (
                [
                    {
                        "id": str(raw_claim.get("citation_id") or "").strip() or new_citation_id(),
                        "claim_id": claim_id,
                        "source_chunk_ids": valid_ids,
                        "review_state": "verified",
                    }
                ]
                if valid_ids
                else []
            )
            claims.append(
                ReportClaim(
                    id=claim_id,
                    section_id=outline_section.id,
                    text=text,
                    claim_type=claim_type,
                    citations=[
                        ClaimCitation.from_dict(item)
                        for item in citations
                    ],
                )
            )
        if not claims:
            gap = (
                f"本次已选证据未能支持“{outline_section.title}”。"
                if report_language == "zh"
                else f"The selected evidence does not support “{outline_section.title}”."
            )
            claim_id = new_claim_id()
            claims = [ReportClaim(id=claim_id, section_id=outline_section.id, text=gap, claim_type="evidence_gap")]
            gap_notes.append(gap)
        if any(claim.claim_type == "evidence_gap" for claim in claims):
            gap_notes.append(f"{outline_section.title} contains an evidence gap.")
        normalized.append(LiteratureReportSection(id=outline_section.id, title=outline_section.title, claims=claims))
    return normalized, list(dict.fromkeys(gap_notes))
