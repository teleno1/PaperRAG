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


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    collapsed = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", collapsed).strip()


def _stem_token(token: str) -> str:
    value = token.strip()
    for suffix in ("ations", "ation", "ingly", "edly", "ingly", "ments", "ment", "ingly", "ing", "edly", "edly", "ed", "es", "s"):
        if len(value) > 5 and value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    if len(value) > 6 and value.endswith("ion"):
        value = value[:-3]
    return value


def _tokenize_text(value: str) -> list[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []
    return [_stem_token(token) for token in normalized.split() if token]


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "source",
    "sources",
    "document",
    "documents",
    "corpus",
    "provided",
    "what",
    "with",
}


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

    has_title = bool(re.search(r"^#\s+\S+", text, flags=re.MULTILINE))
    has_bullets = bool(re.search(r"^-\s+", text, flags=re.MULTILINE))
    has_citation = "[Sources:" in text
    return 1.0 if has_title and has_bullets and has_citation else 0.0


ABSTENTION_CUES = (
    "not in the provided sources",
    "not documented",
    "cannot determine",
    "insufficient information",
    "not available in the provided sources",
    "the provided sources do not",
    "the corpus does not contain",
    "the provided corpus does not contain",
    "does not contain information",
    "none of the retrieved sources",
    "no source in the corpus mentions",
    "not possible based on the given sources",
    "not possible based on the provided sources",
)


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


def _scoring_fragments(output_content: str, output_format: ReportFormat) -> list[str]:
    text = output_content.strip()
    if not text:
        return []

    if output_format == "json":
        payload = _load_report_payload(text)
        if payload is None:
            return []
        fragments: list[str] = []
        overview = str(payload.get("overview", "")).strip()
        if overview:
            fragments.append(overview)
        for section in payload.get("sections", []):
            body = str(section.get("body", "")).strip()
            if body:
                fragments.append(body)
        return fragments

    fragments = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        stripped = re.sub(r"\[Sources:\s*.+?\]\s*$", "", stripped).strip()
        fragments.append(stripped)
    return fragments


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


def _token_overlap_ratio(needle_tokens: list[str], haystack_tokens: list[str]) -> float:
    if not needle_tokens:
        return 0.0
    matches = 0
    for token in needle_tokens:
        if any(
            token == candidate
            or (len(token) >= 5 and candidate.startswith(token))
            or (len(candidate) >= 5 and token.startswith(candidate))
            for candidate in haystack_tokens
        ):
            matches += 1
    return matches / len(needle_tokens)


def _is_abstaining_fragment(fragment: str, aspect: str) -> bool:
    normalized_fragment = _normalize_text(fragment)
    normalized_aspect = _normalize_text(aspect)
    if not normalized_fragment or not normalized_aspect:
        return False
    if any(_normalize_text(cue) in normalized_fragment for cue in ABSTENTION_CUES):
        return True

    negation_markers = (
        "do not document",
        "does not document",
        "not documented",
        "no source",
        "no sources",
        "not mentioned",
        "not specified",
        "not describe",
        "not describe any",
        "lack",
        "lacks",
        "absence of",
        "without",
        "no information",
    )
    return any(marker in normalized_fragment and normalized_aspect in normalized_fragment for marker in negation_markers)


def answer_point_coverage(output_content: str, output_format: ReportFormat, answer_points: list[str]) -> float:
    normalized_points = [_normalize_text(point) for point in answer_points if _normalize_text(point)]
    if not normalized_points:
        return 0.0

    fragments = _scoring_fragments(output_content, output_format)
    normalized_fragments = [_normalize_text(fragment) for fragment in fragments]
    tokenized_fragments = [_tokenize_text(fragment) for fragment in fragments]

    covered = 0
    for point in normalized_points:
        if any(point in fragment for fragment in normalized_fragments):
            covered += 1
            continue
        point_tokens = [token for token in _tokenize_text(point) if token not in STOPWORDS]
        if not point_tokens:
            continue
        overlap = max((_token_overlap_ratio(point_tokens, fragment_tokens) for fragment_tokens in tokenized_fragments), default=0.0)
        if overlap >= 0.5:
            covered += 1
    return covered / len(normalized_points)


def unsupported_aspect_violation_count(
    output_content: str,
    output_format: ReportFormat,
    unsupported_aspects: list[str],
) -> int:
    fragments = _scoring_fragments(output_content, output_format)
    normalized_fragments = [_normalize_text(fragment) for fragment in fragments if _normalize_text(fragment)]
    if not normalized_fragments:
        return 0

    violations = 0
    for aspect in unsupported_aspects:
        normalized_aspect = _normalize_text(aspect)
        if not normalized_aspect:
            continue
        matching_fragments = [fragment for fragment in normalized_fragments if normalized_aspect in fragment]
        if matching_fragments and any(not _is_abstaining_fragment(fragment, aspect) for fragment in matching_fragments):
            violations += 1
    return violations


def abstention_cue_present(output_content: str, output_format: ReportFormat) -> bool:
    normalized_output = " ".join(_normalize_text(fragment) for fragment in _scoring_fragments(output_content, output_format))
    return any(_normalize_text(cue) in normalized_output for cue in ABSTENTION_CUES)


class GenerationCaseMetrics(BaseModel):
    citation_hit_rate: float
    unknown_citation_count: int
    format_compliance: float
    no_source_assertion_rate: float
    answer_point_coverage: float
    unsupported_aspect_violation_count: int
    abstention_cue_present: bool


class GenerationAggregateMetrics(BaseModel):
    citation_hit_rate: float
    unknown_citation_count: int
    format_compliance_rate: float
    no_source_assertion_rate: float
    answer_point_coverage: float
    unsupported_aspect_violation_count: int
    abstention_cue_rate: float
    case_count: int


def build_generation_case_metrics(
    *,
    cited_source_ids: list[str],
    expected_source_ids: list[str],
    retrieved_source_ids: list[str],
    output_content: str,
    output_format: ReportFormat,
    answer_points: list[str] | None = None,
    unsupported_aspects: list[str] | None = None,
) -> GenerationCaseMetrics:
    return GenerationCaseMetrics(
        citation_hit_rate=citation_hit_rate(cited_source_ids, expected_source_ids, retrieved_source_ids),
        unknown_citation_count=unknown_citation_count(cited_source_ids, retrieved_source_ids),
        format_compliance=format_compliance(output_content, output_format),
        no_source_assertion_rate=no_source_assertion_rate(output_content, output_format),
        answer_point_coverage=answer_point_coverage(output_content, output_format, answer_points or []),
        unsupported_aspect_violation_count=unsupported_aspect_violation_count(
            output_content,
            output_format,
            unsupported_aspects or [],
        ),
        abstention_cue_present=abstention_cue_present(output_content, output_format),
    )


def aggregate_generation_metrics(case_metrics: list[GenerationCaseMetrics]) -> GenerationAggregateMetrics:
    if not case_metrics:
        return GenerationAggregateMetrics(
            citation_hit_rate=0.0,
            unknown_citation_count=0,
            format_compliance_rate=0.0,
            no_source_assertion_rate=0.0,
            answer_point_coverage=0.0,
            unsupported_aspect_violation_count=0,
            abstention_cue_rate=0.0,
            case_count=0,
        )

    case_count = len(case_metrics)
    return GenerationAggregateMetrics(
        citation_hit_rate=sum(item.citation_hit_rate for item in case_metrics) / case_count,
        unknown_citation_count=sum(item.unknown_citation_count for item in case_metrics),
        format_compliance_rate=sum(item.format_compliance for item in case_metrics) / case_count,
        no_source_assertion_rate=sum(item.no_source_assertion_rate for item in case_metrics) / case_count,
        answer_point_coverage=sum(item.answer_point_coverage for item in case_metrics) / case_count,
        unsupported_aspect_violation_count=sum(item.unsupported_aspect_violation_count for item in case_metrics),
        abstention_cue_rate=sum(1.0 for item in case_metrics if item.abstention_cue_present) / case_count,
        case_count=case_count,
    )
