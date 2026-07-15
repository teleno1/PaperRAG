# 07 - Accept the Complete Workspace Interaction Prototype

**Type:** prototype

**What to build:** A Workspace Owner can select, combine, and iteratively refine
the candidate experience into one high-fidelity desktop Interaction Prototype,
then accept the complete Interaction Contract that production browser work must
implement.

**Blocked by:** None. 06 completed on 2026-07-15.

**Status:** complete

**Claimed by:** Codex (2026-07-15)

- [x] The owner-selected or hybrid architecture covers the entire Prototype
  Journey Boundary: workspace setup; import/discovery; readiness and recovery;
  outline and automatic retrieval; report generation; draft editing; citation
  inspection and review; Report Trust Summary; and Markdown export.
- [x] Controlled scenarios make queued, running, succeeded, failed,
  interrupted, and cancelled operations, chapter retries, evidence gaps,
  partial readiness, multi-source citations, unavailable original PDFs, and
  direct-edit or AI-rewrite review outcomes operable rather than static.
- [x] An Interaction Contract records every visible state, control location and
  enablement, transition and recovery path, confirmation/editing rule, and
  mapped domain object. Each iteration records the owner's changes.
- [x] Closure requires explicit Workspace Owner acceptance. Prototype code stays
  isolated and disposable; its accepted contract, not mocked implementation,
  is the input to later delivery tickets.

## Iteration record

- **2026-07-15 — selected direction:** Owner selected the iterated flow-driven
  desktop workspace. Fixed product/navigation chrome; independently scrollable
  task and detail panes; import-management tabs; grouped, collapsible outline
  chapters with editable section queries and versioning; continuous clickable
  writing text with source detail in the Task Detail Pane. A standalone
  evidence-curation stage was intentionally removed from the prototype; the
  outline query is the owner-visible retrieval control.
- **2026-07-15 — contract draft:**
  [Workspace Interaction Contract](../../../docs/specs/workspace-interaction-contract.md)
  records the selected controls and their first implementation boundary. It is
  awaiting the Owner's explicit final acceptance and completion of the
  remaining prototype-only recovery scenarios before this ticket can close.
- **2026-07-15 — recovery scenario pass:** Added the in-memory **07 验收场景台**
  to the isolated prototype. It operates partial readiness; queued, running,
  succeeded, failed, interrupted, and cancelled operations; failed-chapter
  retry; evidence gaps; multi-source source selection; unavailable-PDF
  recovery; direct-edit/AI-rewrite review state; and a trust-summary Markdown
  export fixture. It is deliberately outside the selected product layout.
- **2026-07-15 — accepted:** The Workspace Owner explicitly accepted the
  selected flow-driven architecture and its Interaction Contract. This ticket
  unblocks ticket 08. The contract supersedes the old separate
  evidence-curation presentation: users version outline queries; automatic
  Chapter Evidence Bundles are frozen with each Report Operation Attempt.
