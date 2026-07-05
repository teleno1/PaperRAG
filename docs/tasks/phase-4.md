# Phase 4 Tasks: Evaluation and Strategy Comparison

## T4-01: Add eval dataset format and loader

Status: done
Phase: Phase 4
Priority: high

Goal:
Create the foundation for objective evaluation.

Allowed Changes:
- Add eval dataset models.
- Add JSONL loader.
- Add tiny sample dataset fixtures.

Acceptance:
- Loader validates `id`, `query`, `expected_sources`, `answer_points`, and
  `output_format`.
- Bad eval rows produce clear errors.
- Tests cover valid and invalid rows.

Verification:
- `python -m pytest -q`

Notes:
- The full 30-question dataset can be added later; this task establishes format.
- Added eval dataset models and a JSONL loader with row-numbered validation errors for malformed JSON, missing fields, unsupported output formats, and blank required values.
- Added a tiny tracked sample dataset at `data/eval_samples/eval_dataset.jsonl` for fixture coverage and later manual eval verification.
- Verification: `python -m pytest -q` -> `90 passed`.
- Review: subagent flagged whitespace-only required values slipping through validation; this was fixed and re-verified with no blocking findings.

## T4-02: Implement retrieval metrics

Status: done
Phase: Phase 4
Priority: high

Goal:
Measure retrieval quality objectively.

Allowed Changes:
- Add metric functions for `Recall@5`, `Recall@10`, and `MRR`.
- Add deterministic unit tests.

Acceptance:
- Metrics work from retrieved source ids and expected source ids.
- Edge cases are covered: no expected sources, empty retrieval, duplicate
  retrieval results.

Verification:
- `python -m pytest -q`

Notes:
- Keep metrics independent from LLM calls.
- Added deterministic retrieval metric helpers for `Recall@5`, `Recall@10`, `MRR`, per-case retrieval counts, and aggregate summaries.
- Duplicate retrieved ids are normalized away before top-k and rank calculations so the metrics stay deterministic across repeated hits.
- Verification: `python -m pytest -q` -> `96 passed`.
- Review: subagent reported no blocking findings; we added a duplicate-boundary regression test and clarified the `avg_retrieved_sources` metric wording in the evaluation plan.

## T4-03: Implement citation and output metrics

Status: done
Phase: Phase 4
Priority: high

Goal:
Measure citation reliability and output format compliance.

Allowed Changes:
- Add `citation_hit_rate`, `unknown_citation_count`, and
  `format_compliance_rate`.
- Reuse existing citation validation ideas where possible.
- Add deterministic tests.

Acceptance:
- Unknown citation ids are counted.
- JSON format compliance uses real JSON parsing.
- Markdown/bullet compliance has simple deterministic checks.

Verification:
- `python -m pytest -q`

Notes:
- Do not rely on LLM judge as the only validation mechanism.
- Added deterministic generation metric helpers for `citation_hit_rate`, `unknown_citation_count`, `format_compliance_rate`, and `no_source_assertion_rate`, plus per-case and aggregate summaries.
- JSON compliance now checks real JSON parsing and basic report payload shape; Markdown and `bullet_summary` use simple structural checks with citation markers.
- Verification: `python -m pytest -q` -> `102 passed`.
- Review: subagent flagged schema-invalid JSON crashes and an unclear `citation_hit_rate` semantic; both were fixed or documented and re-verified with no blocking findings.

## T4-04: Add eval CLI, API, and output artifacts

Status: done
Phase: Phase 4
Priority: high

Goal:
Run evaluation from CLI and save reproducible artifacts.

Allowed Changes:
- Add `python -m app.cli.main eval run`.
- Add `POST /eval/run`.
- Save `metrics.json`, `cases.jsonl`, `failures.jsonl`, and `retrieval_debug.jsonl`.
- Add tests using fake retrieval and generation.

Acceptance:
- CLI command accepts `--dataset`.
- API route accepts dataset.
- Eval output path is under `data/eval_outputs/<run_id>/`.
- Metrics file is resume-friendly and deterministic for test fixtures.

Verification:
- `python -m pytest -q`
- `python -m app.cli.main eval run --dataset data/eval_samples/eval_dataset.jsonl`

Notes:
- If sample dataset is not present yet, add a tiny one in this task or mark the
  manual eval command as blocked with reason.
- Added `RunEvalUseCase`, eval result models, CLI `eval run`, and API `POST /eval/run`, with artifacts written under `data/eval_outputs/<run_id>/`.
- Eval runs now use the currently configured retrieval/index path by default, while case report artifacts are redirected into `eval_outputs/<run_id>/case_outputs/` for reproducible inspection.
- Retrieval metrics now use one ranked identifier per retrieved result, while citation metrics still validate against retrieved source ids; fixture tests pin deterministic latency/artifact content through an injected timer.
- Verification: `python -m pytest -q` -> `109 passed`; `python -m app.cli.main eval run --dataset data/eval_samples/eval_dataset.jsonl` completed and wrote metrics/cases/failures/retrieval debug artifacts.
- Review: subagent initially flagged metric-id inflation, hidden sample-corpus evaluation, nondeterministic fixture artifacts, and roadmap drift; all must-fix issues were addressed and a final re-review reported no blocking findings.

## T4-05: Add strategy comparison

Status: todo
Phase: Phase 4
Priority: medium

Goal:
Compare chunking, retrieval top-k, and reranking strategies with metrics.

Allowed Changes:
- Add config or CLI options for strategy selection.
- Add comparison output table or JSON.
- Add tests for strategy result aggregation.

Acceptance:
- At least two chunking strategies can be compared.
- At least two retrieval top-k settings can be compared.
- Rerank on/off can be compared if rerank support exists.
- Output includes metrics per strategy.

Verification:
- `python -m pytest -q`

Notes:
- Keep strategy comparison small and inspectable.
