---
type: prototype
status: closed
claimed_by: Codex
blocked_by: []
resolved: 2026-07-12
---

# Prototype the Report Editor and Evidence-Trace Interaction

## Question

What minimal browser flow makes topic entry, paper selection, outline approval,
report editing, claim-level citations, and pending-review citations legible to
a first-time research user?

Produce a cheap interactive or static prototype to discuss with the user. It
must show a claim with multiple sources, the evidence side panel, and the
post-edit pending-review state.

## Prototype

[Interactive evidence-trace prototype](02-evidence-trace-prototype.html)

The throwaway browser artifact contains three deliberately different layouts,
switchable with `?variant=A|B|C` or its bottom switcher. It uses in-memory
example data only. The selected A layout demonstrates topic entry, Candidate
and Selected Paper distinction, readiness, outline approval, report editing,
a Claim Citation with two sources, and a content edit that exposes pending
review with keep, remove, and workspace-scoped refresh actions.

## Resolution

The first-version default is **A: guided workspace**. It makes the reporting
workflow visible rather than treating the report editor as an isolated writing
surface:

- A compact timeline at the top shows topic, paper selection, outline approval,
  report editing, and citation review.
- The left column holds the topic and paper boundary, including Selected Paper
  readiness and Candidate Papers that cannot enter evidence.
- The central column contains the approved Report Outline and editable
  Literature Report; citation markers attach to individual Claims.
- A persistent right evidence panel opens from a citation marker and shows all
  cited Source Chunks with paper title, page or section, clean excerpt,
  Citation Revision, and workspace/readiness boundary.
- A substantive Claim edit changes the visible state to pending review and
  exposes user-confirm, remove, and refresh actions. Refresh is labelled as
  restricted to the ready Selected Papers in the current Research Workspace.

The report-first and evidence-ledger variants are retained only as prototype
evidence. They are not production layout decisions.
