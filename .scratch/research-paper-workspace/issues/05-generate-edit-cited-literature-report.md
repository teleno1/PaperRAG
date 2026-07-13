# 05 — Generate and Edit a Cited Literature Report

**What to build:** A researcher can generate an editable Literature Report in
the browser from an approved Report Outline and ready Selected Papers. The
report honours the workspace Report Language and preserves stable, one-to-many
Claim Citations rather than flattening evidence into untraceable text.

**Blocked by:** 04 — Generate, Edit, and Approve a Report Outline.

**Status:** paused pending 04A acceptance

**Stabilization dependency:** 04A must be browser-accepted before this ticket
resumes. Its Candidate Paper, outline-history, layout, and discovery recovery
flows are prerequisites for the Literature Report workflow.

- [ ] Generation uses the current workspace topic, Report Language, approved
  outline, and only ready Selected Papers, while recording its Evidence
  Coverage.
- [ ] Each supported report Claim retains one or more validated Claim Citations
  with stable identity across persisted report data, API responses, and the
  browser editor.
- [ ] A researcher can make ordinary browser edits to an automatically persisted
  Report Draft without losing report structure or source history.
- [ ] Missing retrieval support and generation failure appear as explicit
  Evidence Gap or recoverable report states, never as fabricated cited content;
  the end-to-end flow has browser-level acceptance coverage.
