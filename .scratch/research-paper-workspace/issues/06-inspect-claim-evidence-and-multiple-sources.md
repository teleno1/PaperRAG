# 06 — Inspect Claim Evidence and Multiple Sources

**What to build:** A researcher can select a Claim Citation in the Literature
Report and inspect all of its evidence in a persistent browser side panel,
including every cited Research Paper, version, source excerpt, page or section
location, and Citation Review State.

**Blocked by:** 05D — Publish a Complete Evidence-Driven Literature Report.

**Status:** ready-for-agent

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

- [ ] A report Claim visibly references one or multiple real retrieved Source
  Chunks, including support from more than one Research Paper.
- [ ] Selecting a Claim Citation reveals paper identity, version provenance,
  excerpt, and page and/or section information when available.
- [ ] The side panel clearly distinguishes verified, pending-review, removed,
  and evidence-unavailable states without misrepresenting historical evidence
  as current evidence.
- [ ] Persistence, API, browser interaction, and a multi-source browser-level
  acceptance test cover the complete evidence-inspection path.
