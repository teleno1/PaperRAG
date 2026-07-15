# Workspace Interaction Contract (draft)

**Status:** accepted by Workspace Owner (2026-07-15)
**Prototype source:** `frontend/prototype.html` / `frontend/src/prototype/`
**Selected architecture:** iterated flow-driven desktop workspace
**Scope:** desktop Interaction Prototype only; no production API, persistence,
or provider behaviour is implied.

## Shell and navigation

| Visible state | Control and location | Rule and result | Domain mapping |
| --- | --- | --- | --- |
| Any active stage | Product title and stage navigation, left column | Remain fixed while the centre and right panes scroll independently. Choosing a stage replaces both task and detail surfaces. | Research Workspace, Workflow Stage, Task Detail Pane |
| Literature import | Left navigation | Opens candidate discovery in the centre and import management in the right pane. | Candidate Paper, Selected Paper, Evidence Readiness |
| Paper reading | Left navigation | Opens the selected ready paper's original-PDF reading fixture and ready-paper library. Missing readiness explains the next permitted action. | Paper Reading View, Selected Paper |
| Report outline | Left navigation | Opens the editable, versioned outline. | Report Outline, Outline Revision |
| Report writing | Left navigation | Opens continuous report text and claim-specific source information. | Literature Report, Focused Claim, Claim Citation |

## Literature import and paper reading

| Visible state | Control and location | Enablement, transition, and recovery | Domain mapping |
| --- | --- | --- | --- |
| Candidate search results | `导入` / `移除`, centre result row | Import adds a Selected Paper record and exposes its operation in the right pane. Removing hides only the Candidate Paper from this result set. | Candidate Paper, Selected Paper |
| Import library — ready tab | `管理` then multi-select and `删除`, right pane | Management mode exposes selection. Deletion removes selected paper records from the visible library and must surface provenance/citation consequences in production. | Selected Paper, Evidence Readiness |
| Import library — in-progress/failed tab | `管理`, multi-select, `中断` / `重试` / `删除记录`, right pane | Retry is available only to failed or interrupted work. Production must preserve the Workspace Operation rule: running work is never force-interrupted; queued work may be cancelled. | Workspace Operation, Evidence Readiness |
| Reading library | Ready-paper row, right pane | Selecting a row changes the centre Paper Reading View. Delete remains an explicit paper action. | Paper Reading View, Selected Paper |
| Citation source jump | Source row in writing detail pane | Opens Paper Reading View at the cited SourceAnchor; if the original PDF is unavailable, show historical metadata/excerpt and recovery/refresh actions rather than a reconstructed reader. | Claim Citation, SourceAnchor, Document Version |

## Report outline and retrieval planning

| Visible state | Control and location | Enablement, transition, and recovery | Domain mapping |
| --- | --- | --- | --- |
| Collapsed outline | Chapter heading, centre | All chapters start collapsed. Selecting a heading expands or collapses its group. Chapter title is stored once per group, never repeated per section card. | Report Outline, chapter |
| Expanded chapter | Chapter title; section title and retrieval-query fields, centre | All fields are directly editable. A query has the same versioning importance as its section content. Ordinary title/order edits preserve section identity; split, merge, or deletion produces a successor revision in production. | Report Outline, section, retrieval query, Outline Revision |
| Outline composition | `添加章节`, `添加小节`, delete chapter, delete section, centre | Adding a chapter creates a new collapsed group; adding a section uses the current chapter. Deletion is explicit and updates the in-memory fixture immediately. Production requires confirmation where loss of a saved revision or generated-report relationship is affected. | Report Outline, Outline Revision |
| Version history | Save, restore, rename version, right pane | A version freezes both chapter/section content and retrieval queries. Restore creates the selected working state; renaming changes only the human-readable label. | Outline Revision |

## Report writing and citation inspection

| Visible state | Control and location | Enablement, transition, and recovery | Domain mapping |
| --- | --- | --- | --- |
| Report draft | Inline report text, centre | The draft is continuous prose rather than sentence cards. A citation-bearing sentence has a modest hover affordance and remains highlighted when focused. | Literature Report, Report Draft, Focused Claim |
| Focused claim | Click cited sentence, centre | Replaces the right pane with title, chunk excerpt, source anchor, and verification status for the claim's Claim Citations. Multiple sources must remain independently selectable. | Focused Claim, Claim Citation, Source Chunk, SourceAnchor |
| Citation status | Source detail, right pane | Show verified, pending review, or evidence-unavailable truthfully. Direct substantive editing moves the citation to pending review; a successful refresh alone restores verified. | Citation Review State, Claim Citation |
| Chapter regeneration | Instruction field and `重新生成`, below chapter | The instruction is scoped to the chapter. Production creates a separate regenerated draft/attempt, preserves the current draft until selection, and displays failed/retryable chapter results without publishing partial output. | Workspace Operation, Report Draft, Report Revision |

## Controlled recovery scenarios

The selected navigation and core interactions above are the Owner-reviewed
baseline. The prototype's floating **07 验收场景台** operates the following
deterministic, in-memory states without becoming part of the product layout:

- workspace setup, empty selected-paper set, partial readiness, queued,
  running, succeeded, failed, interrupted, and cancelled operation states;
- failure retry, per-chapter report retry, evidence-gap presentation, and
  multi-source citation inspection;
- unavailable original-PDF recovery; direct-edit pending review; AI-rewrite
  review outcomes; report trust summary; and Markdown export;
- the owner-visible retrieval-query editing above is the selected replacement
  for the historical separate evidence-curation presentation. The product
  specification and downstream delivery tickets still require a deliberate
  documentation reconciliation after contract acceptance.

## Acceptance record

The Workspace Owner explicitly accepted this contract on 2026-07-15 after the
selected workspace and controlled recovery scenarios were reviewed. It is now
the browser-acceptance source. The prototype remains disposable; later delivery
tickets implement this contract, not its fixture code.
