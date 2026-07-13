# 03 — Prepare a Research Workspace in the Browser

**What to build:** A researcher can create or revisit a Research Workspace in
the same-origin browser application, set its topic and Report Language, upload
a Research Paper, discover Candidate Papers, import or select papers, and see
their Evidence Readiness and recoverable next actions.

**Blocked by:** 01 — Create a Research Workspace and Select Uploaded Papers;
02 — Discover and Import Open Research Papers. Both are complete, so this
ticket can start immediately.

**Status:** ready-for-agent

- [ ] The browser provides a usable workspace entry flow for the completed
  workspace, authorised-upload, discovery, import, selection, and removal
  capabilities, rather than requiring direct API use.
- [ ] Candidate Papers and unselected or not-ready Selected Papers are visibly
  distinguished from evidence eligible for downstream work.
- [ ] Upload, import, and processing operations expose persisted progress,
  success, failure, and recovery state in the browser.
- [ ] The production FastAPI application serves the compiled browser workspace
  and its versioned workspace APIs from the same origin, with browser-level
  acceptance coverage for the preparation flow.
