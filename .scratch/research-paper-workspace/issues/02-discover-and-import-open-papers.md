# 02 — Discover and Import Open Research Papers

**What to build:** A researcher can search open academic sources from a
Research Workspace, inspect Candidate Paper metadata, and select an openly
available PDF for import. Restricted, duplicate, missing, and non-PDF results
remain visible with an understandable status and do not become evidence.

**Blocked by:** Wayfinder decision: Research open-paper discovery and import
adapters; 01 — Create a Research Workspace and Select Uploaded Papers.

**Status:** complete (resolved 2026-07-12; claimed by Codex)

**Active blockers (supersedes the historical Wayfinder reference above):** 01.

- [x] A topic search returns Candidate Papers with enough provenance and
  metadata for the user to decide whether to select them.
- [x] The system imports only publicly available PDFs automatically and records
  the result in the current Research Workspace.
- [x] Import failures and restricted papers preserve their metadata and provide
  a next action rather than silently disappearing.
- [x] Candidate Papers cannot influence retrieval or Claim Citations until the
  user selects and the system successfully processes them.

## Delivery notes

- Added injectable OpenAlex and arXiv discovery adapters with persisted
  provider/DOI/arXiv/source-link metadata and workspace-scoped deduplication.
- Added bounded, MIME/signature-verified public PDF download and a durable
  selected-paper import operation. Restricted or unavailable candidates remain
  visible with an authorised-upload next action; an authorised upload can attach
  to that candidate, and failed downloads are retryable.
- Persisted version-level requested/final URLs, retrieval time, SHA-256, and
  version-scoped parsed/chunk artifacts; replacement requires explicit
  `replace=true` and creates a new Document Version.
- Added versioned API routes for discovery and selected-candidate import under
  `/api/workspaces/{workspace_id}/papers/discover` and
  `/api/workspaces/{workspace_id}/papers/{paper_id}/import`.
- Verification: `python -m pytest -q tests/test_discovery_adapters.py tests/test_workspace_discovery.py tests/test_workspace_discovery_api.py tests/test_workspace_api.py tests/test_workspace_flow.py` (28 passed).
