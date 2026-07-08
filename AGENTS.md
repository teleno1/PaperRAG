# AGENTS.md

PaperRAG is being refactored from an academic paper-review pipeline into a
general, trustworthy knowledge-base RAG system. The refactor is mid-flight:
legacy paper-review code and new document-centric code coexist intentionally.
Compatibility layers bridge the two until old code can be safely removed.

The roadmap is in [docs/refactor-roadmap.md](docs/refactor-roadmap.md); task
tracking is in [TASKS.md](TASKS.md). Read both before working.

## Coupling Points

The following legacy concepts are still referenced across the codebase. They
are intentional transitional artifacts — do not remove them unless the active
phase explicitly calls for it:

- `paper_id` — used throughout ingestion, indexing, and retrieval as a
  compatibility key alongside the newer `document_id`.
- `review`, `outline`, `chapter` — the old academic paper review pipeline.
  These domain packages still exist and some tests exercise them.
- `content_list_v2.json` — the old MinerU ingestion manifest, still
  referenced by index building and compatibility paths.

## Hard Constraints

- Never commit API keys, `.env` files, or secrets of any kind.
- Never commit generated indexes, parsed corpora, run outputs, eval outputs,
  caches, or large local documents.
- Do not delete tracked `data/` artifacts unless the active phase explicitly
  requires it and the specific paths have been verified.
- Do not perform broad package/module renames without tests passing before and
  after the change.
- Do not use `git reset --hard`.
- Do not replace the project with a new toy demo — reuse the existing working
  skeleton where it helps.
- Do not introduce heavyweight infrastructure unless it directly supports the
  roadmap acceptance criteria.
- Do not add a frontend during this refactor unless a later phase explicitly
  requests it.

## Git Rules

- Work on the current phase branch (e.g. `phase/4-evaluation`). Do not create
  a new branch per task.
- After each completed task, create a checkpoint commit. Use the task ID as
  the commit message (e.g. `T4-04 add eval CLI output artifacts`).
- If a task fails and cannot be fixed, roll back only that task's changes.
  Do not touch files modified by other tasks.

## Coding Approach

- Prefer compatibility layers and adapters before renaming or deleting modules.
- Introduce domain-level abstractions (e.g. `Document`, `DocumentChunk`) before
  removing old paper-specific code.
- Keep CLI and API entrypoints working unless the active phase explicitly
  changes them.
- Keep changes small and testable. If behavior must change, update tests in the
  same phase and explain why.
- Only modify files within the active task's acceptance criteria. If a needed
  change falls outside scope, stop and report.
- If a change touches architecture, API surface, or evaluation rules, update
  the corresponding docs (`docs/architecture.md`, `docs/evaluation-plan.md`,
  `docs/refactor-roadmap.md`) in the same task.

## Task Execution

- Read AGENTS.md, TASKS.md, and the roadmap. Then execute all tasks in the
  current phase sequentially. Do not stop between tasks unless a stop
  condition is triggered.
- For each task:
  1. Read the task details from `docs/tasks/phase-N.md`.
  2. Implement the changes. Stay within the task's acceptance scope.
  3. Run the task's verification.
  4. If verification passes, update the task status in the phase file and
     TASKS.md, then create a checkpoint commit.
  5. Run a subagent code review (see below).
  6. Proceed to the next task.
- When all tasks in the phase are complete, run the phase-level verification,
  commit any final doc updates, and report completion.

## Code Review

After each task passes verification, run a subagent code review. Focus on:
behavior regression, test coverage gaps, scope creep, and AGENTS.md
violations. If the review finds must-fix issues, fix them, re-verify, then
commit. Advisory findings can be noted in the task's Notes field without
blocking progress.

## Stop Conditions

Stop and report immediately if:

- A task's verification fails after two fix attempts.
- A code review finds high-risk issues that persist after two fix attempts.
- TASKS.md contradicts the actual code state.
- A task requires deleting large amounts of tracked data, adding heavy new
  dependencies, or changing the tech stack.
- A needed change falls outside the current task's acceptance criteria.
- All tasks in the current phase are complete.

## Handoff

After completing a phase, report:
- Each task completed, with its commit hash.
- Test results per task and phase-level verification outcome.
- Code review findings and resolutions.
- Docs updated.
- Current Active Task in TASKS.md.
- Next recommended phase.

## Agent skills

### Issue tracker

Issues are tracked in this repo's GitHub Issues. External PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

This repo uses the default five-label triage vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This repo uses a single-context domain-doc layout centered on a root `CONTEXT.md` and `docs/adr/` when they exist. See `docs/agents/domain.md`.
