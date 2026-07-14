# 05 — Generate and Edit a Cited Literature Report

**What to build:** A researcher can generate an editable Literature Report in
the browser from an approved Report Outline and ready Selected Papers. The
report honours the workspace Report Language and preserves stable, one-to-many
Claim Citations rather than flattening evidence into untraceable text.

**Blocked by:** 04 — Generate, Edit, and Approve a Report Outline.

**Status:** complete

**Resolved:** 2026-07-14

**Claimed by:** Codex

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

- [x] Generation uses the current workspace topic, Report Language, approved
  outline, and only ready Selected Papers, while recording its Evidence
  Coverage.
- [x] Each supported report Claim retains one or more validated Claim Citations
  with stable identity across persisted report data, API responses, and the
  browser editor.
- [x] A researcher can make ordinary browser edits to an automatically persisted
  Report Draft without losing report structure or source history.
- [x] Missing retrieval support and generation failure appear as explicit
  Evidence Gap or recoverable report states, never as fabricated cited content;
  the end-to-end flow has browser-level acceptance coverage.

## Delivery notes

- Added workspace-scoped Literature Report, Claim, Claim Citation, Source Chunk,
  and Evidence Coverage models with stable IDs and explicit evidence-gap state.
- Added SQLite-backed report drafts and durable `generate_report` operations,
  including a ready-subset input snapshot, safe failure state, and retry path.
- Added scoped chunk retrieval from the active Document Version of ready
  Selected Papers; generated citations are filtered against that source registry.
- Added report generation, draft read/save, and workspace-embedded API responses,
  plus a minimal browser editor with evidence coverage, gap notes, citation
  markers, and debounced automatic persistence.

## Verification

- `python -m pytest -q` — 181 passed, 4 warnings.
- `python -m compileall -q app` — passed.
- `npm.cmd run build` from `frontend/` — passed.
- `npm.cmd exec playwright test` from `frontend/` — 2 browser scenarios passed
  in the available Chrome runtime.
