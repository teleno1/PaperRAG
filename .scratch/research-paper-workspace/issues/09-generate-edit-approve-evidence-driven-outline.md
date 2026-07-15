# 09 - Generate, Edit, and Approve an Evidence-Driven Outline

**What to build:** A researcher with ready Selected Papers can generate, edit,
save, regenerate, and approve a real evidence-driven Report Outline in the
accepted outline stage, with its saved versions available for review.

**Blocked by:** 08 - Connect Preparation and Reading to the Accepted Workspace.

**Status:** ready-for-agent

- [ ] Planning retrieval derives three to five topic-and-question queries from
  ready workspace evidence and stores a representative Planning Evidence Bundle
  of roughly 12-20 MMR-ranked Chunks with at most two from each paper.
- [ ] `deepseek-v4-flash` receives the accepted prompt contract and returns
  schema-validated JSON with abstract, body, conclusion-and-outlook, and
  references roles; body sections have editable title, objective, expected
  claims, and at least one retrieval query.
- [ ] The outline stage preserves role/order constraints, IDs, revisions,
  planning-evidence and model/prompt snapshots, visible operation failure and
  retry, and an explicit approval action. It does not decide final body
  evidence; that begins in ticket 10.
- [ ] Controlled tests and a documented real-provider manual acceptance run
  demonstrate actual planning retrieval and outline generation in the accepted
  workspace interface, with no fixed-outline fallback.

