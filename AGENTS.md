# AGENTS.md

PaperRAG is changing from a general knowledge-base RAG refactor into a
single-user research-paper reading and reporting workspace. The active product
goal is: users define a topic, select uploaded or discovered papers, generate
an editable literature report, and trace each cited claim to one or more paper
chunks in the interface.

Read [CONTEXT.md](CONTEXT.md) and the active
[Wayfinder map](docs/wayfinder/research-paper-workspace.md) before working.
The old phase plan and generic-RAG task list are historical material; see
[docs/legacy/README.md](docs/legacy/README.md).

## Product Boundaries

- A `Research Paper` is the primary source type; a `Document` remains the
  underlying ingestible abstraction.
- A `Research Workspace` contains one topic, its selected papers, ingestion and
  index state, reports, and provenance records.
- Search results are `Candidate Papers`; only `Selected Papers` may be parsed,
  indexed, retrieved, or cited.
- Online discovery may automatically import only open-access PDFs. Never scrape
  or import restricted full text.
- A `Claim Citation` is a one-to-many link from a report claim to source chunks.
  Substantially editing a cited claim moves it to pending review.
- The first version is single-user, browser-based, and exports Markdown.
  Collaboration, account systems, and PDF/Word export are out of scope.

## Hard Constraints

- Never commit API keys, `.env` files, or secrets of any kind.
- Never commit generated indexes, parsed corpora, report runs, eval outputs,
  caches, or large local papers.
- Do not delete tracked `data/` artifacts without verifying the exact paths and
  the active ticket's need.
- Do not use `git reset --hard`.
- Reuse the existing Python/FastAPI, parsing, chunking, vector-store, and
  citation-validation foundation where it supports the active product.
- Do not add heavyweight infrastructure without a direct, accepted product need.
- Frontend work is allowed only when it follows the active Wayfinder decision or
  ticket; do not substitute a toy demo for the workspace workflow.

## Working Approach

- Treat [docs/wayfinder/research-paper-workspace.md](docs/wayfinder/research-paper-workspace.md)
  as the current planning source of truth. Resolve its open tickets before
  starting dependent implementation.
- Prefer small, testable compatibility layers to broad renames or deletions.
- Preserve current CLI/API flows until a product ticket deliberately replaces or
  adapts them.
- Keep domain terminology aligned with [CONTEXT.md](CONTEXT.md).
- When a change affects architecture, product flow, API surface, provenance, or
  evaluation, update the relevant active documentation in the same task.
- For completed implementation tasks: run the ticket verification, update the
  local ticket/map status, run a focused code review, and create a checkpoint
  commit with the ticket identifier.

## Stop Conditions

Stop and report if a required change is outside the active ticket, verification
fails after two fix attempts, a high-risk review finding persists after two
attempts, or the task requires restricted-content ingestion, broad unverified
deletion, or a technology change not yet decided in the map.

## Domain Documentation

This repository uses a single root [CONTEXT.md](CONTEXT.md) and `docs/adr/`
for durable architectural decisions. See [docs/agents/domain.md](docs/agents/domain.md).
