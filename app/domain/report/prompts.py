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
        "Reuse source wording when it directly answers the request. "
        "Every factual section must cite at least one source id. "
        "If the sources are insufficient, say exactly `The provided sources do not document ...` "
        "for the missing topic and cite the nearest boundary-defining source ids. "
        "Do not invent unsupported details, defaults, prices, limits, or timelines."
    )
    prompt = (
        f"User request:\n{query}\n\n"
        "Retrieved sources JSON:\n"
        f"{_format_sources(retrieved_sources)}\n\n"
        "Write a concise grounded report. Prefer 1-3 sections. "
        "Mirror exact phrases from the sources when possible so the answer stays close to the corpus. "
        "When the answer is partial, separate supported facts from unsupported facts. "
        "When the answer is unavailable, state that the provided sources do not document it.\n\n"
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
