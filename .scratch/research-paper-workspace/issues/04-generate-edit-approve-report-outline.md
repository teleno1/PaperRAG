# 04 — Generate, Edit, and Approve a Report Outline

**What to build:** A researcher with ready Selected Papers can generate a
default Report Outline in the browser, add, remove, rename, and reorder its
sections, then explicitly approve the Outline Revision that will guide a
Literature Report.

**Blocked by:** 03 — Prepare a Research Workspace in the Browser.

**Status:** ready-for-agent

- [ ] Outline generation uses only evidence eligible in the current Research
  Workspace; empty or not-yet-ready paper sets produce an understandable next
  action instead of an apparently valid outline.
- [ ] The browser supports editing the research question, methods and findings,
  comparison, limitations or gaps, conclusion, and references before approval.
- [ ] Approval persists an immutable Outline Revision and its state survives a
  browser refresh; editing an approved outline returns the new current revision
  to draft without rewriting prior history.
- [ ] The full outline flow is covered through persistence, API, browser UI,
  and browser-level acceptance tests.
