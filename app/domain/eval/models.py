from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

EvalOutputFormat = Literal["markdown", "json", "bullet_summary"]


class EvalDatasetRow(BaseModel):
    id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    expected_sources: list[str] = Field(..., min_length=1)
    answer_points: list[str] = Field(..., min_length=1)
    output_format: EvalOutputFormat
    tags: list[str] = Field(default_factory=list)

    @field_validator("id", "query")
    @classmethod
    def _validate_non_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be blank")
        return normalized

    @field_validator("expected_sources", "answer_points", "tags")
    @classmethod
    def _validate_string_lists(cls, values: list[str]) -> list[str]:
        normalized_values: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if not normalized:
                raise ValueError("List items must not be blank")
            normalized_values.append(normalized)
        return normalized_values


class EvalDataset(BaseModel):
    rows: list[EvalDatasetRow] = Field(default_factory=list)
