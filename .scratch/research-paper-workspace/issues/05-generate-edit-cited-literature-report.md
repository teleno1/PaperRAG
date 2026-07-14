# 05 — Generate and Edit a Cited Literature Report

**What to build:** A researcher can generate an editable Literature Report in
the browser from an approved Report Outline and ready Selected Papers. The
report honours the workspace Report Language and preserves stable, one-to-many
Claim Citations rather than flattening evidence into untraceable text.

**Blocked by:** 04 — Generate, Edit, and Approve a Report Outline.

**Status:** ready-for-agent

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

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
