# 10 — Implement the Accepted Research Workspace Prototype

**What to build:** A researcher can use the accepted Research Workspace
interaction model against real persisted workspaces, operations, reports, and
Claim Citations. The final browser experience completes the existing product
workflow without relying on mock data or losing its evidence and recovery
semantics.

**Blocked by:** 09 — Prototype the Final Research Workspace Experience.

**Status:** ready-for-agent

- [ ] The accepted information architecture and interaction model drive the
  real same-origin workspace APIs, persisted Workspace Operations, report
  revisions, Claim Citations, and Markdown export.
- [ ] Every user-visible state from tickets 01 through 08, including failures,
  retries, Evidence Coverage, evidence gaps, and Citation Review State, remains
  truthful and usable in the final interface.
- [ ] Existing functional behaviour is preserved or deliberately migrated with
  browser-level acceptance coverage for the complete research workflow.
- [ ] The final interface is responsive and accessible, while keeping domain
  and API behaviour independent from presentation components.
