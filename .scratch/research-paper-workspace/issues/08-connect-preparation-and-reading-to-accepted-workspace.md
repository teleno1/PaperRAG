# 08 - Connect Preparation and Reading to the Accepted Workspace

**What to build:** A researcher can use the accepted desktop workspace to
create a real Workspace, upload or discover Selected Papers, recover from
preparation failures, and read any ready paper in its authorised original PDF.

**Blocked by:** 07 - Accept the Complete Workspace Interaction Prototype.

**Status:** complete

**Resolved:** 2026-07-17

**Claimed by:** Codex (2026-07-17)

- [x] Production browser state is supplied through the accepted Workspace View
  State contract and implements the accepted import and paper-reading stages;
  all Workflow Stages remain visible, while unavailable stages explain their
  prerequisite and offer the next permitted action.
- [x] The import stage provides upload and open-paper search, an operation list
  with truthful progress/failure/retry, and a distinct ready-paper collection;
  it preserves Candidate Paper and Selected Paper boundaries.
- [x] The paper-reading stage renders the active authorised original PDF rather
  than reconstructed Chunk text, lets the user switch ready papers, and reports
  unavailable historical PDFs truthfully without a synthetic reader.
- [x] API, persistence, browser acceptance, and regression tests cover the
  real preparation/read path and verify that the prototype fixture is not used
  in production.

## Delivery notes

- Added a production `Workspace View State` boundary on
  `/api/workspaces/{workspace_id}/view`, including stage gating, grouped import
  state, reading state, outline/report summaries, and next-action metadata for
  unavailable stages.
- Added an authorised-original PDF route on
  `/api/workspaces/{workspace_id}/papers/{paper_id}/pdf` that serves only the
  managed local source file for the requested workspace paper and returns a
  truthful `paper_pdf_unavailable` error instead of reconstructing a reader
  from chunks.
- Replaced the historical preparation browser shell with the accepted
  four-stage workspace. Literature Import now separates ready papers, selected
  papers still preparing, dismissed candidates, and durable workspace
  operations; Paper Reading uses the production PDF route and preserves the
  accepted blocked-stage guidance.
- Added import/recovery affordances that match the delivered boundary:
  authorised-PDF upload for selected candidates, retry/remove actions, ready
  paper switching from the reading library, and restore controls for dismissed
  candidate papers.

## Verification

- `python -m pytest -q` - 190 passed, 4 warnings.
- `npm.cmd run build` from `frontend/` - passed.
- `npm.cmd run test:e2e` from `frontend/` - 2 passed.
