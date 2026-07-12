# 02 — Discover and Import Open Research Papers

**What to build:** A researcher can search open academic sources from a
Research Workspace, inspect Candidate Paper metadata, and select an openly
available PDF for import. Restricted, duplicate, missing, and non-PDF results
remain visible with an understandable status and do not become evidence.

**Blocked by:** Wayfinder decision: Research open-paper discovery and import
adapters; 01 — Create a Research Workspace and Select Uploaded Papers.

**Status:** ready-for-agent

**Active blockers (supersedes the historical Wayfinder reference above):** 01.

- [ ] A topic search returns Candidate Papers with enough provenance and
  metadata for the user to decide whether to select them.
- [ ] The system imports only publicly available PDFs automatically and records
  the result in the current Research Workspace.
- [ ] Import failures and restricted papers preserve their metadata and provide
  a next action rather than silently disappearing.
- [ ] Candidate Papers cannot influence retrieval or Claim Citations until the
  user selects and the system successfully processes them.
