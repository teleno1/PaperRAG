from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

from app.domain.report.models import ReportFormat


def _normalize_ids(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def citation_hit_rate(
    cited_source_ids: list[str],
    expected_source_ids: list[str],
    retrieved_source_ids: list[str],
) -> float:
    cited = _normalize_ids(cited_source_ids)
    if not cited:
        return 0.0
    supported = set(_normalize_ids(expected_source_ids)) | set(_normalize_ids(retrieved_source_ids))
    hit_count = sum(1 for source_id in cited if source_id in supported)
    return hit_count / len(cited)


def unknown_citation_count(cited_source_ids: list[str], retrieved_source_ids: list[str]) -> int:
    cited = _normalize_ids(cited_source_ids)
    retrieved = set(_normalize_ids(retrieved_source_ids))
    return sum(1 for source_id in cited if source_id not in retrieved)


def format_compliance(output_content: str, output_format: ReportFormat) -> float:
    text = output_content.strip()
    if not text:
        return 0.0

    if output_format == "json":
        payload = _load_report_payload(text)
        if payload is None:
            return 0.0
        return 1.0

    if output_format == "markdown":
        has_title = bool(re.search(r"^#\s+\S+", text, flags=re.MULTILINE))
        has_cited_body = "[Sources:" in text and "## " in text
        return 1.0 if has_title and has_cited_body else 0.0

    has_bullets = bool(re.search(r"^-\s+", text, flags=re.MULTILINE))
    has_cited_bullet = bool(re.search(r"^-\s+.*\[Sources:\s*.+\]$", text, flags=re.MULTILINE))
    return 1.0 if has_bullets and has_cited_bullet else 0.0


FACT_MARKERS = (
    "should",
    "must",
    "supports",
    "validates",
    "includes",
    "preserve",
    "carry",
    "use",
    "improve",
    "prevent",
    "require",
    "explains",
    "shows",
)


def _is_fact_like(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in FACT_MARKERS) or bool(re.search(r"\b\d+\b", lowered))


def _load_report_payload(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("title"), str):
        return None

    sections = payload.get("sections")
    if not isinstance(sections, list):
        return None

    for section in sections:
        if not isinstance(section, dict):
            return None
        if not isinstance(section.get("title"), str):
            return None
        if not isinstance(section.get("body"), str):
            return None
        cited_source_ids = section.get("cited_source_ids", [])
        if not isinstance(cited_source_ids, list):
            return None
        if any(not isinstance(item, str) for item in cited_source_ids):
            return None

    return payload


def _uncited_fact_rate_from_lines(lines: list[str]) -> float:
    fact_like_lines = [line.strip() for line in lines if _is_fact_like(line)]
    if not fact_like_lines:
        return 0.0
    uncited = [line for line in fact_like_lines if "[Sources:" not in line]
    return len(uncited) / len(fact_like_lines)


def no_source_assertion_rate(output_content: str, output_format: ReportFormat) -> float:
    text = output_content.strip()
    if not text:
        return 0.0

    if output_format == "json":
        payload = _load_report_payload(text)
        if payload is None:
            return 1.0
        sections = payload.get("sections", [])
        lines = []
        for section in sections:
            body = section.get("body", "").strip()
            cited_source_ids = section.get("cited_source_ids", []) or []
            if not body:
                continue
            suffix = f" [Sources: {', '.join(cited_source_ids)}]" if cited_source_ids else ""
            lines.append(body + suffix)
        return _uncited_fact_rate_from_lines(lines)

    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    return _uncited_fact_rate_from_lines(lines)


class GenerationCaseMetrics(BaseModel):
    citation_hit_rate: float
    unknown_citation_count: int
    format_compliance: float
    no_source_assertion_rate: float


class GenerationAggregateMetrics(BaseModel):
    citation_hit_rate: float
    unknown_citation_count: int
    format_compliance_rate: float
    no_source_assertion_rate: float
    case_count: int


def build_generation_case_metrics(
    *,
    cited_source_ids: list[str],
    expected_source_ids: list[str],
    retrieved_source_ids: list[str],
    output_content: str,
    output_format: ReportFormat,
) -> GenerationCaseMetrics:
    return GenerationCaseMetrics(
        citation_hit_rate=citation_hit_rate(cited_source_ids, expected_source_ids, retrieved_source_ids),
        unknown_citation_count=unknown_citation_count(cited_source_ids, retrieved_source_ids),
        format_compliance=format_compliance(output_content, output_format),
        no_source_assertion_rate=no_source_assertion_rate(output_content, output_format),
    )


def aggregate_generation_metrics(case_metrics: list[GenerationCaseMetrics]) -> GenerationAggregateMetrics:
    if not case_metrics:
        return GenerationAggregateMetrics(
            citation_hit_rate=0.0,
            unknown_citation_count=0,
            format_compliance_rate=0.0,
            no_source_assertion_rate=0.0,
            case_count=0,
        )

    case_count = len(case_metrics)
    return GenerationAggregateMetrics(
        citation_hit_rate=sum(item.citation_hit_rate for item in case_metrics) / case_count,
        unknown_citation_count=sum(item.unknown_citation_count for item in case_metrics),
        format_compliance_rate=sum(item.format_compliance for item in case_metrics) / case_count,
        no_source_assertion_rate=sum(item.no_source_assertion_rate for item in case_metrics) / case_count,
        case_count=case_count,
    )
