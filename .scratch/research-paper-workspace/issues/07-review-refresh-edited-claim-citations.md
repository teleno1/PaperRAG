# 07 — Review and Refresh Edited Claim Citations

**What to build:** When a researcher substantively changes a cited report Claim
in the browser, its Claim Citation becomes pending review. The researcher can
keep it, remove it, or refresh it using only the current Research Workspace's
ready Selected Papers, and sees the resulting Citation Review State.

**Blocked by:** 06 — Inspect Claim Evidence and Multiple Sources.

**Status:** ready-for-agent

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

- [ ] A substantive edit never leaves an affected Claim Citation displayed as
  verified; presentation-only changes preserve its Citation Review State.
- [ ] The browser exposes keep, remove, and refresh actions with explicit,
  persisted resulting states and Citation Revision history.
- [ ] Refresh uses the workspace-scoped vector index and support validation; it
  cannot attach a Source Chunk outside the current workspace's ready Selected
  Papers or preserve an unknown source identifier.
- [ ] Refresh with no supporting evidence ends in a clear pending or unresolved
  state rather than inventing a citation, with complete persistence, API, and
  browser-level acceptance coverage.
