# Phase 0 Tasks: Repository Slimming and Context Setup

## T0-01: Update `.gitignore` for generated artifacts

Status: todo
Phase: Phase 0
Priority: high

Goal:
Keep generated data, indexes, parsed corpora, run outputs, eval outputs, and
caches out of git.

Allowed Changes:
- Update `.gitignore`.
- Add comments that distinguish source-controlled sample data from local
  generated artifacts.

Acceptance:
- `.gitignore` covers `data/database/`, `data/processed_papers/`,
  `data/review_outputs/`, `data/eval_outputs/`, and common local caches.
- Any intended sample-data path remains allowed and documented.
- No business code is changed.

Verification:
- `python -m pytest -q`
- `git status --short`

Notes:
- Do not delete or untrack data in this task.

## T0-02: Audit and slim `data/`

Status: todo
Phase: Phase 0
Priority: high

Goal:
Separate local research artifacts from tiny source-controlled samples.

Allowed Changes:
- Inventory tracked files under `data/`.
- Remove or relocate large generated artifacts after confirming exact paths.
- Keep a tiny sample corpus if needed for tests or README demos.

Acceptance:
- Large local corpora, parsed results, indexes, and run outputs are no longer
  treated as source files.
- A minimal sample-data strategy is documented.
- Existing tests still pass.

Verification:
- `python -m pytest -q`
- `git status --short`
- `git ls-files data`

Notes:
- Be careful: this task may delete tracked files. Verify paths before removing
  anything.

## T0-03: Update README with the refactor direction

Status: todo
Phase: Phase 0
Priority: medium

Goal:
Make the README explain that the project is being refactored from PaperRAG into
a general trustworthy RAG system.

Allowed Changes:
- Update README project description, current status, and roadmap summary.
- Link to `AGENTS.md`, `TASKS.md`, and docs.

Acceptance:
- README states the target product clearly.
- README includes current verification command.
- README does not claim unfinished features are already complete.

Verification:
- `python -m pytest -q`

Notes:
- Keep README honest: distinguish current behavior from target behavior.

