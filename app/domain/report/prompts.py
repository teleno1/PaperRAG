from __future__ import annotations

import json

from app.domain.retrieval.models import RetrievedSource


def _format_sources(retrieved_sources: list[RetrievedSource]) -> str:
    payload = []
    for source in retrieved_sources:
        payload.append(
            {
                "source_id": source.source_id,
                "document_id": source.document_id,
                "paper_id": source.paper_id,
                "chunk_id": source.chunk_id,
                "title": source.title,
                "section": source.section,
                "content": source.content,
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_report_prompts(query: str, retrieved_sources: list[RetrievedSource]) -> tuple[str, str]:
    system_prompt = (
        "You are a grounded report-writing assistant for a retrieval-augmented system. "
        "Use only the provided sources. "
        "Return exactly one JSON object with keys `title`, `overview`, and `sections`. "
        "Each section must include `title`, `body`, and `cited_source_ids`. "
        "`cited_source_ids` must contain only source ids from the provided sources. "
        "If the sources are insufficient, say so clearly and keep citations conservative."
    )
    prompt = (
        f"User request:\n{query}\n\n"
        "Retrieved sources JSON:\n"
        f"{_format_sources(retrieved_sources)}\n\n"
        "Return a JSON object in this shape:\n"
        '{\n'
        '  "title": "report title",\n'
        '  "overview": "brief overview",\n'
        '  "sections": [\n'
        '    {\n'
        '      "title": "section title",\n'
        '      "body": "section body",\n'
        '      "cited_source_ids": ["source-id-1"]\n'
        '    }\n'
        "  ]\n"
        "}"
    )
    return system_prompt, prompt
