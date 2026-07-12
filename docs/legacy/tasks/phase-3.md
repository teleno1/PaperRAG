# Phase 3 Tasks: Cited Answers and Reports

## T3-01: Add cited answer use case

Status: done
Phase: Phase 3
Priority: high

Goal:
Support query -> retrieval -> cited answer generation.

Allowed Changes:
- Add answer domain/use-case models.
- Add a generation path that consumes retrieved sources and emits source ids.
- Add tests with fake retrieval and fake LLM clients.

Acceptance:
- Answer output includes text and cited source ids.
- Citations can be validated against retrieved source registry.
- Existing review flow remains available.

Verification:
- `python -m pytest -q`

Notes:
- Keep prompts domain-neutral.
- Added a general `RunQueryUseCase` that retrieves sources, asks the LLM for structured JSON, and validates cited source ids against the retrieved source registry.
- Retrieved sources now expose `document_id` when available and preserve `paper_id` compatibility for older metadata records.
- Verification: `python -m pytest -q` -> `70 passed`.
- Review: subagent found and we fixed a default `top_k` regression; final review reported no blocking findings.

## T3-02: Add report generation use case

Status: done
Phase: Phase 3
Priority: medium

Goal:
Generate configurable reports, not only academic reviews.

Allowed Changes:
- Add report request/response models.
- Support `markdown`, `json`, and `bullet_summary` output modes.
- Add tests for format compliance with fake LLM output.

Acceptance:
- Markdown output includes title/body/citations.
- JSON output is parseable.
- Bullet summary output is structured and cited.

Verification:
- `python -m pytest -q`

Notes:
- Do not remove old `review` commands in this task.
- Added a general `RunReportUseCase` that retrieves sources, asks the LLM for one canonical JSON report payload, validates cited source ids, and renders local `markdown`, `json`, or `bullet_summary` outputs.
- Report artifacts now persist under `outputs_dir/reports/<run_id>/` with canonical report JSON, retrieved source snapshots, and validation metadata.
- Verification: `python -m pytest -q` -> `76 passed`.
- Review: subagent flagged invalid citations leaking into outputs and a `latest_run_dir` regression for nested report runs; both were fixed and re-verified.
- Follow-up note: shared path helpers and README still describe the older single-layer run layout, so future surfaces should keep that inconsistency in mind.

## T3-03: Add CLI/API query and report entrypoints

Status: done
Phase: Phase 3
Priority: high

Goal:
Expose the general RAG product surface.

Allowed Changes:
- Add CLI commands for query/report.
- Add FastAPI routes for query/report.
- Mark old review commands as compatibility or deprecated if appropriate.

Acceptance:
- CLI can run a cited answer flow against an existing index.
- API exposes query/report endpoints.
- Existing health/state routes remain working.

Verification:
- `python -m pytest -q`
- `python -m app.cli.main health`

Notes:
- Keep API route logic thin; call use cases.
- Added `query run` and `report run` CLI commands that call the new use cases and print structured JSON outputs.
- Added `POST /query` and `POST /report` FastAPI endpoints with traceable source metadata and explicit `ErrorResponse` payloads on failures.
- Review commands/routes remain available as legacy compatibility surfaces.
- Verification: `python -m pytest -q` -> `84 passed`; `python -m app.cli.main health` -> healthy JSON response.
- Review: subagent flagged parser-level CLI dispatch and API error-schema mismatches; both were fixed and re-verified with no blocking findings.
