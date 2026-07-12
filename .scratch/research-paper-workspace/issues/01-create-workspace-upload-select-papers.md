# 01 — Create a Research Workspace and Select Uploaded Papers

**What to build:** A researcher can create a Research Workspace, select its
Chinese or English Report Language, upload an authorised PDF, see its processing
state, and explicitly make it a Selected Paper. Only a Selected Paper is usable
as workspace evidence; an upload that fails processing gives the user a clear,
recoverable status.

**Blocked by:** Wayfinder decisions: Model the Research Workspace and
provenance contract; Prototype the report editor and evidence-trace interaction;
Audit stable PDF source-location anchors; Choose the single-user application
topology.

**Status:** complete

**Resolved:** 2026-07-12

**Claimed by:** Codex

**Active blockers (supersedes the historical Wayfinder references above):** None.

- [x] A user can create and revisit a single-user workspace with topic and
  Report Language.
- [x] A user can upload an authorised PDF, see readiness or a recoverable
  processing failure, and select or remove the resulting Research Paper.
- [x] Unselected or unsuccessfully processed papers cannot be used as evidence
  by downstream workspace operations.
- [x] The workflow is available through the chosen browser/API surface and is
  covered with fake-based external-service tests.

## Delivery notes

- Added SQLite-backed workspace, paper, Document Version, and Workspace
  Operation persistence under the configured local workspace directory.
- Added `/api/workspaces` creation/list/revisit routes, PDF upload processing,
  select/remove routes, and `/api/operations/{id}` polling.
- Direct authorised uploads enter the selected-paper boundary; only a selected
  paper with ready evidence is reported as evidence-eligible. Parser failures
  remain visible as retryable, non-evidence paper state.
- External PDF parsing is injected through the existing `ParserRegistry` seam;
  tests use a controlled fake parser and never call a provider.

## Verification

- `python -m pytest -q tests/test_workspace_flow.py tests/test_workspace_api.py`
- `python -m pytest -q`
