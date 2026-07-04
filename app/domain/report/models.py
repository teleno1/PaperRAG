from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.answer.models import AnswerValidation
from app.domain.retrieval.models import RetrievedSource

ReportFormat = Literal["markdown", "json", "bullet_summary"]


class ReportRequest(BaseModel):
    query: str
    output_format: ReportFormat = "markdown"
    top_k: int = 5


class ReportSection(BaseModel):
    title: str
    body: str
    cited_source_ids: list[str] = Field(default_factory=list)


class GeneratedReport(BaseModel):
    title: str
    overview: str = ""
    sections: list[ReportSection] = Field(default_factory=list)

    def all_cited_source_ids(self) -> list[str]:
        source_ids: list[str] = []
        for section in self.sections:
            source_ids.extend(section.cited_source_ids)
        return source_ids

    def to_pretty_json(self) -> str:
        return json.dumps(self.model_dump(), ensure_ascii=False, indent=2)

    def sanitized(self, allowed_source_ids: set[str]) -> GeneratedReport:
        sanitized_sections: list[ReportSection] = []
        for section in self.sections:
            cited_source_ids: list[str] = []
            seen: set[str] = set()
            for source_id in section.cited_source_ids:
                value = str(source_id).strip()
                if not value or value not in allowed_source_ids or value in seen:
                    continue
                seen.add(value)
                cited_source_ids.append(value)
            sanitized_sections.append(
                section.model_copy(
                    update={
                        "cited_source_ids": cited_source_ids,
                    }
                )
            )
        return self.model_copy(update={"sections": sanitized_sections})


class ReportResult(BaseModel):
    run_id: str
    run_dir: Path
    query: str
    output_format: ReportFormat
    output_path: Path
    report_json_path: Path
    retrieved_sources_path: Path
    validation_path: Path
    content: str
    report: GeneratedReport
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    validation: AnswerValidation
