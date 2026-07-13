# 03 — Prepare a Research Workspace in the Browser

**What to build:** A researcher can create or revisit a Research Workspace in
the same-origin browser application, set its topic and Report Language, upload
a Research Paper, discover Candidate Papers, import or select papers, and see
their Evidence Readiness and recoverable next actions.

**Blocked by:** 01 — Create a Research Workspace and Select Uploaded Papers;
02 — Discover and Import Open Research Papers. Both are complete, so this
ticket can start immediately.

**Status:** complete

**Resolved:** 2026-07-13

**Claimed by:** Codex

- [x] The browser provides a usable workspace entry flow for the completed
  workspace, authorised-upload, discovery, import, selection, and removal
  capabilities, rather than requiring direct API use.
- [x] Candidate Papers and unselected or not-ready Selected Papers are visibly
  distinguished from evidence eligible for downstream work.
- [x] Upload, import, and processing operations expose persisted progress,
  success, failure, and recovery state in the browser.
- [x] The production FastAPI application serves the compiled browser workspace
  and its versioned workspace APIs from the same origin, with browser-level
  acceptance coverage for the preparation flow.

## Delivery notes

- Added a separately runnable React + TypeScript workspace application with a
  three-column preparation layout for paper boundary, discovery/upload actions,
  and durable operation activity.
- Added same-origin FastAPI delivery for the compiled SPA, client-side route
  fallback, and a Vite development proxy for `/api`.
- Workspace responses now include persisted operation history, with a dedicated
  workspace operation-history endpoint so browser refresh can recover progress
  and retry actions.
- Added offline API/static delivery coverage and a Playwright browser acceptance
  scenario covering create, discovery, authorised upload, evidence readiness,
  operation success, and removal.

## Verification

- `npm.cmd run build` (frontend typecheck and production build)
- `python -m pytest -q tests/test_workspace_frontend.py tests/test_workspace_api.py tests/test_workspace_discovery_api.py`
- `python -m pytest -q`
- `npm.cmd run test:e2e` requires an installed Playwright browser; the current
  execution environment reported no available in-app browser, so this command
  was not run here.
