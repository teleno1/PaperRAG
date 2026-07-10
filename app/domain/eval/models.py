from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EvalOutputFormat = Literal["markdown", "json", "bullet_summary"]
AnswerExpectation = Literal["full_answer", "partial_answer", "abstain"]
QuestionShape = Literal[
    "single_hop",
    "multi_source_synthesis",
    "parameter_constraint",
    "boundary_comparison",
    "high_distraction_negative",
]


class EvalDatasetRow(BaseModel):
    id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    expected_sources: list[str] = Field(..., min_length=1)
    answer_expectation: AnswerExpectation = "full_answer"
    question_shape: QuestionShape = "single_hop"
    answer_points: list[str] = Field(default_factory=list)
    unsupported_aspects: list[str] = Field(default_factory=list)
    output_format: EvalOutputFormat
    tags: list[str] = Field(default_factory=list)

    @field_validator("id", "query")
    @classmethod
    def _validate_non_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value must not be blank")
        return normalized

    @field_validator("expected_sources", "answer_points", "unsupported_aspects", "tags")
    @classmethod
    def _validate_string_lists(cls, values: list[str]) -> list[str]:
        normalized_values: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if not normalized:
                raise ValueError("List items must not be blank")
            normalized_values.append(normalized)
        return normalized_values

    @model_validator(mode="after")
    def _validate_eval_contract(self) -> EvalDatasetRow:
        if not self.expected_sources:
            raise ValueError("expected_sources must not be empty")

        if self.answer_expectation == "full_answer":
            if not self.answer_points:
                raise ValueError("answer_points must not be empty for full_answer")
            if self.unsupported_aspects:
                raise ValueError("unsupported_aspects must be empty for full_answer")
            return self

        if self.answer_expectation == "partial_answer":
            if not self.answer_points:
                raise ValueError("answer_points must not be empty for partial_answer")
            if not self.unsupported_aspects:
                raise ValueError("unsupported_aspects must not be empty for partial_answer")
            return self

        if self.answer_points:
            raise ValueError("answer_points must be empty for abstain")
        if not self.unsupported_aspects:
            raise ValueError("unsupported_aspects must not be empty for abstain")
        return self


class EvalDataset(BaseModel):
    rows: list[EvalDatasetRow] = Field(default_factory=list)
