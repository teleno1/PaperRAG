from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.exceptions import EvaluationDatasetError
from app.domain.eval.loader import load_eval_dataset


def test_eval_dataset_loader_reads_valid_jsonl(tmp_path: Path) -> None:
    dataset_path = tmp_path / "eval_dataset.jsonl"
    dataset_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "eval-001",
                        "query": "Summarize ingestion requirements.",
                        "expected_sources": ["product_notes"],
                        "answer_expectation": "full_answer",
                        "question_shape": "single_hop",
                        "answer_points": ["TXT ingestion should work without MinerU"],
                        "unsupported_aspects": [],
                        "output_format": "markdown",
                        "tags": ["ingestion"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "id": "eval-002",
                        "query": "Summarize chunk traceability.",
                        "expected_sources": ["retrieval_playbook"],
                        "answer_expectation": "partial_answer",
                        "question_shape": "boundary_comparison",
                        "answer_points": ["document identifiers", "chunk identifiers"],
                        "unsupported_aspects": ["pdf parsing credential requirements for txt files"],
                        "output_format": "json",
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    dataset = load_eval_dataset(dataset_path)

    assert len(dataset.rows) == 2
    assert dataset.rows[0].id == "eval-001"
    assert dataset.rows[0].tags == ["ingestion"]
    assert dataset.rows[1].answer_expectation == "partial_answer"
    assert dataset.rows[1].output_format == "json"


def test_eval_dataset_loader_rejects_invalid_json(tmp_path: Path) -> None:
    dataset_path = tmp_path / "eval_dataset.jsonl"
    dataset_path.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(EvaluationDatasetError) as exc_info:
        load_eval_dataset(dataset_path)

    message = str(exc_info.value)
    assert "Invalid JSON on row 1" in message
    assert exc_info.value.row_number == 1


def test_eval_dataset_loader_rejects_missing_required_field(tmp_path: Path) -> None:
    dataset_path = tmp_path / "eval_dataset.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "eval-001",
                "expected_sources": ["product_notes"],
                "answer_points": ["TXT ingestion should work without MinerU"],
                "output_format": "markdown",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvaluationDatasetError) as exc_info:
        load_eval_dataset(dataset_path)

    message = str(exc_info.value)
    assert "Invalid row 1" in message
    assert "query: Field required" in message


def test_eval_dataset_loader_rejects_unsupported_output_format(tmp_path: Path) -> None:
    dataset_path = tmp_path / "eval_dataset.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "eval-001",
                "query": "Summarize ingestion requirements.",
                "expected_sources": ["product_notes"],
                "answer_points": ["TXT ingestion should work without MinerU"],
                "output_format": "bullets",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvaluationDatasetError) as exc_info:
        load_eval_dataset(dataset_path)

    assert "output_format" in str(exc_info.value)


def test_eval_dataset_loader_rejects_blank_required_values(tmp_path: Path) -> None:
    dataset_path = tmp_path / "eval_dataset.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "   ",
                "query": "   ",
                "expected_sources": [""],
                "answer_points": ["   "],
                "output_format": "markdown",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvaluationDatasetError) as exc_info:
        load_eval_dataset(dataset_path)

    message = str(exc_info.value)
    assert "id: Value must not be blank" in message
    assert "query: Value must not be blank" in message
    assert "expected_sources: List items must not be blank" in message
    assert "answer_points: List items must not be blank" in message


def test_eval_dataset_loader_enforces_partial_answer_contract(tmp_path: Path) -> None:
    dataset_path = tmp_path / "eval_dataset.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "eval-001",
                "query": "What is supported?",
                "expected_sources": ["product_notes"],
                "answer_expectation": "partial_answer",
                "question_shape": "parameter_constraint",
                "answer_points": ["txt ingestion"],
                "unsupported_aspects": [],
                "output_format": "markdown",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvaluationDatasetError) as exc_info:
        load_eval_dataset(dataset_path)

    assert "unsupported_aspects must not be empty for partial_answer" in str(exc_info.value)


def test_eval_dataset_loader_enforces_abstain_contract(tmp_path: Path) -> None:
    dataset_path = tmp_path / "eval_dataset.jsonl"
    dataset_path.write_text(
        json.dumps(
            {
                "id": "eval-001",
                "query": "What pricing tier should I use?",
                "expected_sources": ["product_notes"],
                "answer_expectation": "abstain",
                "question_shape": "high_distraction_negative",
                "answer_points": ["pricing"],
                "unsupported_aspects": ["pricing"],
                "output_format": "markdown",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(EvaluationDatasetError) as exc_info:
        load_eval_dataset(dataset_path)

    assert "answer_points must be empty for abstain" in str(exc_info.value)


def test_tracked_eval_sample_dataset_is_loadable() -> None:
    dataset_path = Path(__file__).resolve().parent.parent / "data" / "eval_samples" / "eval_dataset.jsonl"

    dataset = load_eval_dataset(dataset_path)

    assert len(dataset.rows) >= 3
    assert {row.output_format for row in dataset.rows} == {"markdown", "json", "bullet_summary"}
