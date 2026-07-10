# Phase 5 Tasks: Evaluation Hardening and Final Quality Validation

## T5-01: Add final eval dataset plan and schema refinements

Status: done
Phase: Phase 5
Priority: high

Goal:
Define the final evaluation dataset structure, coverage buckets, and any
minimal schema support needed for the acceptance pass.

Allowed Changes:
- Update `docs/evaluation-plan.md`.
- Add minimal eval schema support needed for the final dataset, such as explicit
  negative or abstention indicators if required.
- Update loader, metric, or result-model tests that need to reflect the final
  evaluation contract.

Acceptance:
- The final dataset contract is specific enough to batch-author the dataset
  without ad hoc decisions.
- Negative or abstention evaluation semantics no longer depend on verbal
  conventions.
- The final corpus boundary is explicit:
  - frozen in-repo snapshot
  - `OpenAI` developer-document ecosystem only
  - `12-18` source documents
  - tracked under `data/eval_corpus/openai_devdocs/`
  - accompanied by a tracked corpus manifest with source URL and snapshot
    provenance
  - document types limited to `guides`, `API reference`, and a small number of
    `cookbook/examples`
  - topical scope limited to `Responses`, `structured outputs`,
    `function calling`, `embeddings`, and `vector-store` or file-search-adjacent
    developer docs
- The final dataset schema explicitly models answer expectation with
  `full_answer`, `partial_answer`, and `abstain`.
- The final dataset schema explicitly models question shape with:
  - `single_hop`
  - `multi_source_synthesis`
  - `parameter_constraint`
  - `boundary_comparison`
  - `high_distraction_negative`
- The final dataset schema explicitly models unsupported content boundaries so
  `partial_answer` and `abstain` cases can be evaluated without guesswork.
- Gold evidence stays at `source_id` granularity; this task must not introduce
  sentence-level or span-level labeling requirements.
- The final dataset authoring plan fixes the target distribution to `40` cases:
  - `24` `full_answer`
  - `8` `partial_answer`
  - `8` `abstain`
- The final dataset authoring plan fixes the output-format distribution to:
  - `20` `markdown`
  - `10` `json`
  - `10` `bullet_summary`
- The final dataset authoring plan also fixes the question-shape buckets:
  - `12` single-hop fact, definition, or constraint lookup cases
  - `10` multi-source or multi-section synthesis cases
  - `8` parameter, limitation, or prerequisite cases
  - `6` boundary or comparison cases
  - `4` high-distraction explicit negative cases

Verification:
- `python -m pytest -q`

Notes:
- Do not create the full `30+` case dataset in this task.
- Negative examples must come from naturally confusing or low-evidence material
  inside the frozen corpus. Do not author artificial distractor documents.
- `expected_sources` should remain meaningful even for `abstain` cases by
  pointing to nearby or boundary-defining sources rather than being left empty.
- Added Phase 5 eval-schema fields for `answer_expectation`,
  `question_shape`, and `unsupported_aspects` with conditional validation that
  keeps the Phase 4 sample fixture backward compatible while enforcing the
  final contract for new rows.
- Added deterministic grading helpers for `answer_point_coverage`,
  `unsupported_aspect_violation_count`, and abstention cue detection, and
  carried those metrics plus case-level `failure_label` into eval artifacts.
- Updated `docs/evaluation-plan.md`, `docs/architecture.md`, and
  `data/README.md` so the enforced Phase 5 contract, eval/API surface, and the
  tracked `data/eval_corpus/openai_devdocs/` boundary are documented alongside
  the code changes.
- Verification: `python -m pytest -q` -> `126 passed`.
- Review: subagent flagged missing branch-level pass/fail tests and a missing
  architecture-doc update for the expanded eval/API surface; both were fixed
  and re-verified with no remaining blocking findings from the standards pass.

## T5-02: Build final 40-case eval dataset

Status: done
Phase: Phase 5
Priority: high

Goal:
Create the final tracked evaluation dataset and frozen corpus from the Phase 5
OpenAI developer-doc snapshot contract.

Allowed Changes:
- Add the final dataset at `data/eval_samples/final_eval_dataset.jsonl`.
- Add the frozen source corpus under `data/eval_corpus/openai_devdocs/`.
- Add a tracked corpus manifest describing provenance and inclusion boundaries.
- Add dataset provenance or authorship notes needed for reproducibility.

Acceptance:
- The dataset contains exactly the planned `40` cases unless the phase task doc
  and evaluation plan are explicitly updated first.
- The dataset follows the `T5-01` answer-expectation contract:
  - `24` `full_answer`
  - `8` `partial_answer`
  - `8` `abstain`
- The dataset follows the `T5-01` question-shape buckets:
  - `12` single-hop fact, definition, or constraint lookup cases
  - `10` multi-source or multi-section synthesis cases
  - `8` parameter, limitation, or prerequisite cases
  - `6` boundary or comparison cases
  - `4` high-distraction explicit negative cases
- The dataset follows the `T5-01` output-format buckets:
  - `20` `markdown`
  - `10` `json`
  - `10` `bullet_summary`
- The dataset uses only the frozen final corpus defined in `T5-01`.
- Low-evidence and abstention cases are grounded in naturally confusing corpus
  slices, not hand-authored fake distractor documents.
- The dataset uses the final schema contract:
  - `answer_expectation` is required
  - `question_shape` is required
  - `unsupported_aspects` is required for `partial_answer` and `abstain`
  - `expected_sources` is non-empty for every case
- The dataset loads through the existing eval loader without manual conversion.

Verification:
- `python -m pytest -q`
- `python -m app.cli.main eval run --dataset data/eval_samples/final_eval_dataset.jsonl`

Notes:
- Do not commit large public raw corpora; keep only small, public, reproducible
  evaluation slices or fixtures.
- Add provenance notes that explain where each frozen source document came from
  and why it is in scope for the final corpus.
- Prefer curated excerpts or snapshots over bulk page dumps so corpus review and
  failure analysis stay human-auditable.
- Author cases as realistic user requests rather than page-title trivia.
- Added a frozen tracked corpus under `data/eval_corpus/openai_devdocs/` with a
  `manifest.json`, `14` curated Markdown source snapshots, and dataset
  authorship notes for reproducibility.
- Added `data/eval_samples/final_eval_dataset.jsonl` with exactly `40` rows and
  tests that lock the answer-expectation, question-shape, and output-format
  distributions plus manifest/source-id integrity.
- Verification: `python -m pytest -q` -> `129 passed`.
- Verification: `python -m app.cli.main eval run --dataset data/eval_samples/final_eval_dataset.jsonl`
  completed after indexing the frozen corpus into the local `data/database/`
  path, but the run failed all `40` cases because the current retrieval and
  generation behavior has not yet been hardened for the final corpus.

## T5-03: Run final eval, analyze failures, and tighten quality

Status: done
Phase: Phase 5
Priority: high

Goal:
Run the final dataset end to end, analyze failures honestly, and close the last
quality gaps needed for acceptance.

Allowed Changes:
- Make small retrieval, citation, format, or eval fixes needed to meet the
  final metric bar.
- Update evaluation docs with final metrics and failure-analysis summaries.

Acceptance:
- Final `metrics.json` is generated from the final dataset.
- Failure cases are inspectable and explained.
- Core metrics reach or are very close to the `T5-04` thresholds, and any
  remaining gap is explicitly recorded.
- Failure analysis distinguishes at least:
  - retrieval miss
  - citation or source-registry failure
  - format-compliance failure
  - unsupported assertion
  - abstention or partial-answer behavior failure

Verification:
- `python -m pytest -q`
- `python -m app.cli.main eval run --dataset data/eval_samples/final_eval_dataset.jsonl`
- `python -m app.cli.main eval compare --dataset data/eval_samples/final_eval_dataset.jsonl --source-dir data/eval_corpus/openai_devdocs`

Notes:
- Limit changes to quality hardening; do not start deployment packaging here.
- Tightened deterministic eval grading without altering the frozen dataset:
  stripped rendered citation suffixes from phrase matching, improved
  abstention-aware unsupported-aspect detection, and kept the `summary/details`
  JSON compatibility shim for report outputs that otherwise failed validation.
- Reverted an intermediate frozen-dataset rewrite after subagent review flagged
  it as out of scope for `T5-03`.
- Removed post-generation citation backfilling after subagent review flagged it
  as a grounding regression; eval now scores the sanitized model output rather
  than invented fallback citations.
- Reverted the synthetic comparison reporter so `eval compare` again uses the
  normal report-generation path.
- Verification: `python -m pytest -q` -> `132 passed`.
- Verification:
  `python -m app.cli.main eval run --dataset data/eval_samples/final_eval_dataset.jsonl`
  -> run `20260710_190826_efc6c4`, `failure_count = 8`,
  `Recall@5 = 1.00`, `citation_hit_rate = 1.00`,
  `unknown_citation_count = 0`, `format_compliance_rate = 1.00`.
- Verification:
  `python -m app.cli.main eval compare --dataset data/eval_samples/final_eval_dataset.jsonl --source-dir data/eval_corpus/openai_devdocs`
  -> run `20260710_192339_c86c53`.
- Review: one subagent flagged an out-of-scope frozen-dataset rewrite and
  missing doc updates; another flagged citation backfilling, over-lenient
  coverage scoring, and a synthetic comparison client. All blocking findings
  were fixed before marking the task done.

## T5-04: Final evaluation acceptance

Status: done
Phase: Phase 5
Priority: high

Goal:
Verify that the project satisfies the evaluation and trustworthiness part of
the Definition of Done.

Allowed Changes:
- Fix small evaluation or documentation gaps found during acceptance.
- Update final evaluation docs.

Acceptance:
- The final dataset contains `40` cases following the `T5-01` and `T5-02`
  contract.
- Metrics satisfy `Recall@5 >= 80%`, `citation_hit_rate >= 90%`,
  `unknown_citation_count = 0`, and `format_compliance_rate >= 90%`.
- Strategy comparison artifacts exist for chunking, retrieval, and rerank.
- At least one success trace and one failure-analysis artifact exist for later
  README or portfolio use.

Verification:
- `python -m pytest -q`
- `python -m app.cli.main eval run --dataset data/eval_samples/final_eval_dataset.jsonl`
- `python -m app.cli.main eval compare --dataset data/eval_samples/final_eval_dataset.jsonl --source-dir data/eval_corpus/openai_devdocs`

Notes:
- This is the quality acceptance pass before deployment and portfolio
  packaging in Phase 6.
- Final acceptance run: `20260710_190826_efc6c4`.
- Acceptance thresholds met:
  `Recall@5 = 1.00`, `citation_hit_rate = 1.00`,
  `unknown_citation_count = 0`, `format_compliance_rate = 1.00`.
- Strategy comparison artifacts written under run
  `20260710_192339_c86c53`, with the lowest failure rate tied between
  `balanced_topk5_rerank_on` and `fine_grained_topk3_rerank_on` at `0.325`.
- `docs/evaluation-plan.md`, `docs/architecture.md`, and
  `docs/refactor-roadmap.md` were updated with final metrics, a successful
  trace, and a failure-analysis summary.
