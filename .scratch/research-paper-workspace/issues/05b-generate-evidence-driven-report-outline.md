# 05B — Generate an Evidence-Driven Report Outline

**What to build:** A researcher with ready Selected Papers can generate, edit,
and approve a real evidence-driven Report Outline rather than a fixed template.
The browser shows the resulting chapters and their retrieval intent before any
Literature Report body is generated.

**Blocked by:** 05A — Index Ready Selected Paper Evidence.

**Status:** ready-for-agent

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

- [ ] Planning retrieval derives three to five topic-and-question queries,
  vector-retrieves ready workspace evidence, and stores a representative
  Planning Evidence Bundle of roughly 12–20 MMR-ranked Chunks with at most two
  from each paper.
- [ ] `deepseek-v4-flash` receives the bounded planning evidence through the
  accepted four-part prompt contract and returns schema-validated JSON: exactly
  one abstract, one or more body chapters with editable sections, one
  conclusion-and-outlook, and one final references chapter. Each body section
  has title, objective, expected claims, and at least one retrieval query.
- [ ] Malformed or invalid JSON gets one validation-error repair attempt, then
  fails the Workspace Operation visibly; production never falls back to a fixed
  outline. Re-generation takes a user instruction and returns a complete new
  Outline Revision.
- [ ] The API, persistence, and minimal browser editor preserve role/order
  constraints, IDs, revisions, planning-evidence and model/prompt snapshots.
  Tests use controlled collaborators, and closure includes a real-provider
  manual outline-generation acceptance run.

