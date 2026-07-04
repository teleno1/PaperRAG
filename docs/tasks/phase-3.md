# Phase 3 Tasks: Cited Answers and Reports

## T3-01: Add cited answer use case

Status: todo
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

## T3-02: Add report generation use case

Status: todo
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

## T3-03: Add CLI/API query and report entrypoints

Status: todo
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

