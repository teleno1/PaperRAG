# 08 — Export Markdown and Demonstrate the Product Workflow

**What to build:** A researcher can export the current Literature Report as
Markdown with Claim Citations and unresolved, pending-review, or
evidence-unavailable states represented truthfully. The project also provides a
repeatable, isolated demonstration of the complete browser workspace workflow.

**Blocked by:** 07 — Review and Refresh Edited Claim Citations.

**Status:** ready-for-agent

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

- [ ] Markdown export preserves report content and Claim Citation references
  without representing unresolved or pending-review citations as verified.
- [ ] A reproducible, isolated 10-paper open-access demonstration workspace
  exercises paper preparation, Selected Paper evidence gating, outline approval,
  cited-report generation, multi-source evidence inspection, and citation
  review; its preflight fails rather than silently using fewer papers.
- [ ] End-to-end tests and user-visible operation state make failures
  inspectable, while automated tests use controlled offline collaborators.
- [ ] Documentation states what the demonstration proves and explicitly does
  not claim enterprise-scale quality from a small corpus.
