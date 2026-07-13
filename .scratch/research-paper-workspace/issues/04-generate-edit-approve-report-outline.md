# 04 — Generate, Edit, and Approve a Report Outline

**What to build:** A researcher with ready Selected Papers can generate a
default Report Outline in the browser, add, remove, rename, and reorder its
sections, then explicitly approve the Outline Revision that will guide a
Literature Report.

**Blocked by:** 03 — Prepare a Research Workspace in the Browser.

**Status:** complete

**Resolved:** 2026-07-13

**Claimed by:** Codex

- [x] Outline generation uses only evidence eligible in the current Research
  Workspace; empty or not-yet-ready paper sets produce an understandable next
  action instead of an apparently valid outline.
- [x] The browser supports editing the research question, methods and findings,
  comparison, limitations or gaps, conclusion, and references before approval.
- [x] Approval persists an immutable Outline Revision and its state survives a
  browser refresh; editing an approved outline returns the new current revision
  to draft without rewriting prior history.
- [x] The full outline flow is covered through persistence, API, browser UI,
  and browser-level acceptance tests.

## Delivery notes

- Added workspace-scoped `ReportOutline` and `OutlineSection` domain models with
  draft/approved lifecycle and ready-evidence snapshots.
- Added SQLite `outline_revisions` persistence, current/history API endpoints,
  queued generation/approval/save operations, operation polling and retry, and a structured
  `outline_unavailable` next action when no ready Selected Paper exists.
- Added browser editing for the research question and section add/remove/rename/
  reorder, explicit save, approval, and approved-revision-to-new-draft flow.
- Added persistence/API tests and extended the Playwright acceptance scenario.

## Verification

- `python -m pytest -q` — 165 passed, 4 warnings.
- `python -m compileall -q app` — passed.
- `npm.cmd run build` from `frontend/` — passed.
- `npx.cmd playwright test --list` from `frontend/` — 1 test discovered.
- Actual Playwright execution remains environment-blocked because Chromium is
  not installed in the available browser runtime.
