# 07 — Export Markdown and Demonstrate the Product Workflow

**What to build:** A researcher can export the current Literature Report as
Markdown, with citation state represented truthfully. The project also has a
repeatable end-to-end demo workspace and product acceptance checks showing
paper selection, report generation, evidence inspection, and citation review.

**Blocked by:** Wayfinder decision: Define product acceptance and demonstration
evidence; 02 — Discover and Import Open Research Papers; 03 — Generate and Edit
a Report Outline; 05 — Inspect Claim Evidence and Multiple Sources; 06 — Review
and Refresh Citations after Editing.

**Status:** ready-for-agent

**Active blockers (supersedes the historical Wayfinder reference above):** 02, 03, 05, 06.

- [ ] Markdown export preserves report content, Claim Citation references, and
  unresolved or pending-review status without representing them as verified.
- [ ] A reproducible, isolated 10-paper OA demo workspace exercises upload or
  discovery, Selected Paper evidence gating, outline approval, cited report
  generation, evidence inspection, and citation review. Its preflight fails
  rather than silently using fewer papers.
- [ ] End-to-end tests and user-visible run state make failures inspectable.
- [ ] Documentation explains what the demo proves and does not claim that a
  small corpus demonstrates enterprise-scale quality.
