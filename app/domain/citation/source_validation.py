from __future__ import annotations

from app.domain.answer.models import AnswerValidation
from app.domain.retrieval.models import RetrievedSource


def _normalize_source_ids(source_ids: list[str]) -> tuple[list[str], list[str]]:
    normalized: list[str] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    for source_id in source_ids:
        value = str(source_id).strip()
        if not value:
            continue
        if value in seen and value not in duplicates:
            duplicates.append(value)
            continue
        seen.add(value)
        normalized.append(value)
    return normalized, duplicates


def validate_cited_source_ids(
    cited_source_ids: list[str],
    retrieved_sources: list[RetrievedSource],
) -> AnswerValidation:
    normalized_ids, duplicates = _normalize_source_ids(cited_source_ids)
    available_source_ids = [source.source_id for source in retrieved_sources if source.source_id]
    available_set = set(available_source_ids)
    unknown_source_ids = [source_id for source_id in normalized_ids if source_id not in available_set]
    return AnswerValidation(
        ok=not unknown_source_ids,
        cited_source_ids=normalized_ids,
        available_source_ids=available_source_ids,
        unknown_source_ids=unknown_source_ids,
        duplicate_source_ids=duplicates,
    )
