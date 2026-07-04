# PaperRAG Codex Handoff Guide

This file is the first thing a coding agent should read when working in this
repository. The project is being refactored from a thesis-oriented paper review
pipeline into a general, trustworthy knowledge-base RAG system.

## Current State

- The existing test baseline is `python -m pytest -q` with 35 passing tests.
- The current product shape is academic paper review generation:
  PDF papers -> MinerU parse -> chunks -> FAISS index -> outline -> review.
- Reusable assets already exist:
  - `app/core`: config, paths, exceptions, logging.
  - `app/api` and `app/cli`: FastAPI and CLI entrypoints.
  - `app/infrastructure/llm`: DeepSeek, DashScope embedding, rerank clients.
  - `app/infrastructure/vectorstore`: FAISS index persistence and build flow.
  - `app/infrastructure/chunking`: useful chunking logic.
  - `app/domain/validation`: citation and source validation ideas.
- The current coupling points are paper-specific names and assumptions:
  `paper_id`, `title/authors/year/venue`, `review`, `outline`, `chapter`,
  `content_list_v2.json`, and MinerU-only ingestion.
- The `data/` directory currently contains large local research artifacts.
  Future cleanup must be deliberate and staged.

## Long-Term Goal

Turn this into a portfolio-grade, general, trustworthy knowledge-base RAG
system with an engineering-verifiable finish line.

The finished system must:

- Ingest at least `PDF`, `TXT`, and `Markdown` documents.
- Run the full RAG flow: clean -> chunk -> embed -> index -> retrieve ->
  generate cited answer/report.
- Generate user-requested output formats such as Markdown, JSON, and concise
  summaries.
- Trace every answer citation back to source `document_id` and `chunk_id`.
- Provide an eval dataset with at least 30 questions.
- Reach `Recall@5 >= 80%` on the eval dataset.
- Reach `citation_hit_rate >= 90%`.
- Reach `unknown_citation_count = 0`.
- Reach output `format_compliance_rate >= 90%`.
- Compare chunking, retrieval, and reranking strategies with metrics.
- Provide README commands that let a fresh environment reproduce the minimal
  demo.

If any critical item above is missing, the project is still in progress.

## Working Rules

- Follow `docs/refactor-roadmap.md`. Work on exactly one phase per task unless
  the user explicitly asks to revise the roadmap.
- Use `TASKS.md` as the short task index, then read only the relevant
  `docs/tasks/phase-*.md` file for the active task details.
- Treat `TASKS.md` as the source of truth for the current active task and final
  Definition of Done.
- Keep changes small and testable. Prefer adding compatibility layers before
  renaming many modules.
- Preserve the current test suite. If behavior must change, update tests in the
  same phase and explain why.
- Prefer domain-level abstractions over string rewrites. Example:
  introduce `Document` and `DocumentChunk` before deleting paper-specific code.
- Keep CLI and API entrypoints working unless the active phase explicitly
  changes them.
- Do not add a frontend during this refactor unless a later phase explicitly
  requests it.

## Hard Constraints

- Never commit API keys, local `.env` files, or secrets in YAML.
- Do not add generated indexes, parsed corpora, run outputs, caches, or large
  documents to git.
- Do not delete tracked `data/` artifacts until Phase 0 explicitly handles repo
  slimming and verifies the intended paths.
- Do not perform broad package/module renames without tests passing before and
  after the change.
- Do not replace the project with a new toy demo. Reuse the existing working
  skeleton where it helps.
- Do not introduce heavyweight infrastructure unless it directly supports the
  roadmap acceptance criteria.

## Required Verification

Run this after each completed phase:

```bash
python -m pytest -q
```

When a phase touches CLI/API behavior, also run the relevant command manually,
for example:

```bash
python -m app.cli.main health
python -m app.cli.main state
```

If tests cannot run because local dependencies or API keys are missing, report
the exact command, error, and remaining risk.

## Communication Pattern

When handing work back, state:

- Which roadmap phase was completed.
- Files changed.
- Verification commands and results.
- Any behavior intentionally left unchanged.
- The next recommended phase.

## Goal Mode Rules

When running in goal mode:
- Execute tasks sequentially from `TASKS.md`.
- Never work on more than one task at a time.
- After each task, run verification, update task status, and create a checkpoint commit.
- Do not continue to the next task if verification fails.
- Stop and report when a task requires destructive data deletion, broad architecture changes beyond its acceptance criteria, or new major dependencies.
