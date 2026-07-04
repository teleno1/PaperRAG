from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.retrieval.models import RetrievedSource


class AnswerRequest(BaseModel):
    query: str
    top_k: int = 5
    include_retrieved_sources: bool = True


class CitedAnswerDraft(BaseModel):
    answer_text: str
    cited_source_ids: list[str] = Field(default_factory=list)


class AnswerValidation(BaseModel):
    ok: bool = True
    cited_source_ids: list[str] = Field(default_factory=list)
    available_source_ids: list[str] = Field(default_factory=list)
    unknown_source_ids: list[str] = Field(default_factory=list)
    duplicate_source_ids: list[str] = Field(default_factory=list)


class AnswerResult(BaseModel):
    query: str
    answer_text: str
    cited_source_ids: list[str] = Field(default_factory=list)
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    validation: AnswerValidation
