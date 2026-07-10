from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.domain.eval.loader import load_eval_dataset


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "data" / "eval_samples" / "final_eval_dataset.jsonl"
MANIFEST_PATH = ROOT / "data" / "eval_corpus" / "openai_devdocs" / "manifest.json"
CORPUS_DIR = MANIFEST_PATH.parent


def test_final_eval_dataset_matches_phase5_distribution_contract() -> None:
    dataset = load_eval_dataset(DATASET_PATH)

    assert len(dataset.rows) == 40

    answer_expectations = Counter(row.answer_expectation for row in dataset.rows)
    question_shapes = Counter(row.question_shape for row in dataset.rows)
    output_formats = Counter(row.output_format for row in dataset.rows)

    assert answer_expectations == {
        "full_answer": 24,
        "partial_answer": 8,
        "abstain": 8,
    }
    assert question_shapes == {
        "single_hop": 12,
        "multi_source_synthesis": 10,
        "parameter_constraint": 8,
        "boundary_comparison": 6,
        "high_distraction_negative": 4,
    }
    assert output_formats == {
        "markdown": 20,
        "json": 10,
        "bullet_summary": 10,
    }
    assert all(row.expected_sources for row in dataset.rows)


def test_final_eval_manifest_is_unique_and_matches_frozen_corpus_files() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    documents = manifest["documents"]

    assert manifest["snapshot_date"] == "2026-07-10"
    assert len(documents) == 14

    doc_ids = [item["doc_id"] for item in documents]
    assert len(doc_ids) == len(set(doc_ids))

    tracked_file_ids = sorted(path.stem for path in CORPUS_DIR.glob("*.md"))
    assert sorted(doc_ids) == tracked_file_ids


def test_final_eval_dataset_expected_sources_resolve_to_manifest_doc_ids() -> None:
    dataset = load_eval_dataset(DATASET_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    doc_ids = {item["doc_id"] for item in manifest["documents"]}

    for row in dataset.rows:
        assert set(row.expected_sources).issubset(doc_ids), row.id
