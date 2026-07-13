# 04A Stabilize Workspace UX and Paper Discovery

**What to build:** Stabilize the 03/04 browser workspace before starting
Literature Report delivery: make the three workspace panels independently
scrollable on desktop, localize the interface in Chinese, let researchers hide
and restore Candidate Papers, expose immutable Report Outline history, and make
OpenAlex discovery and public-PDF import recoverable under quota limits and
unstable source locations.

**Blocked by:** 03 Prepare a Research Workspace in the Browser; 04 Generate,
Edit, and Approve a Report Outline.

**Status:** complete

**Resolved:** 2026-07-13

**Claimed by:** Codex

- [x] Desktop panels have independent scrolling and sticky headings; mobile
  returns to normal page scrolling without layout jumps.
- [x] User-facing workspace copy is Chinese while OpenAlex, arXiv, DOI, PDF,
  and original paper titles remain unchanged; report language remains a
  per-workspace Chinese/English setting.
- [x] Candidate Papers can be dismissed and restored without deleting the
  paper record, document versions, or provenance; dismissed papers stay hidden
  from repeated searches.
- [x] Outline history is read-only, and restoring a revision creates a new
  draft instead of changing an approved revision.
- [x] OpenAlex accepts an environment-only API key, uses `per_page`, caches and
  coalesces duplicate searches, spaces requests, exposes rate-limit recovery
  metadata, and keeps arXiv as an explicit manual fallback.
- [x] Public PDF import records multiple candidate URLs, tries them in order,
  and validates the `%PDF-` signature rather than trusting Content-Type.

## Delivery notes

- Added workspace-scoped `dismissed_at` and persisted ordered PDF URL lists,
  with startup migration for existing SQLite databases.
- Added Candidate Paper dismiss/restore routes and Outline Revision restore as
  a new draft, plus browser controls for both flows.
- Added OpenAlex key handling through `OPENALEX_API_KEY`, in-process caching and
  request coalescing, `Retry-After`/reset-window metadata, and explicit
  configuration or manual provider-switch guidance.
- Added PDF fallback and signature validation while continuing to reject HTML,
  login pages, paywalls, and other non-PDF responses.

## Verification

- `python -m pytest -q` — 177 passed, 4 warnings.
- `python -m compileall -q app` — passed.
- `npm.cmd run build` from `frontend/` — passed.
- `npm.cmd exec playwright test tests/prepare-workspace.spec.ts` — 1 passed
  using the installed Chrome channel; the bundled Playwright Chromium was not
  present in the environment.
