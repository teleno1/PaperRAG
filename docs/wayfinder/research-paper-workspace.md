# Wayfinder: Research-Paper Workspace Product Direction

> Local tracker fallback. GitHub Issues is the configured tracker, but its
> connected integration does not have permission to create issues in this
> repository. This document and its linked local tickets are the canonical
> planning map until GitHub write access becomes available.

## Destination

Define and deliver a single-user research-paper workspace: users set a topic,
upload or discover and select papers, read authorised original PDFs, curate
retrieved evidence, generate an editable literature report, and trace every
cited claim to its source evidence in the desktop interface.

## Notes

- Product focus: individual researchers and graduate students, not a
  general-purpose RAG platform.
- The active specification is [Research-Paper Workspace](../specs/research-paper-workspace.md).
  Its domain vocabulary is in [CONTEXT.md](../../CONTEXT.md).
- The accepted Interaction Prototype, rather than a historical layout, decides
  the desktop information architecture before unfinished browser work begins.
- A ticket is open until its decision or delivery is recorded in the ticket.
  Tickets are claimed locally by adding `Claimed by` before work begins.

## Decisions so far

- [First-version product boundary](research-paper-workspace/closed/00-first-version-product-boundary.md)
  - Single-user browser literature-report workspace with selected papers as its
    only evidence, claim-level provenance, and Markdown export.
- [Research open-paper discovery and import adapters](research-paper-workspace/closed/03-paper-discovery-research.md)
  - Use OpenAlex for topic discovery, arXiv for direct selected-paper import,
    and a guarded OpenAlex OA-PDF fallback; only a verified PDF becomes
    evidence.
- [Audit stable PDF source-location anchors](research-paper-workspace/closed/04-pdf-location-anchor-audit.md)
  - Propagate a versioned SourceAnchor with page range, section, and clean
    excerpt through Chunks, retrieval, and persisted Claim Citations.
- [Research Workspace and provenance contract](research-paper-workspace/closed/01-workspace-provenance-contract.md)
  - Use immutable workspace-scoped identities and revision snapshots; only a
    ready Selected Paper's active Document Version may be new evidence.
- [Report editor and evidence-trace interaction](research-paper-workspace/closed/02-evidence-trace-prototype.md)
  - Historical prototype only. Its fixed guided three-panel layout is
    superseded by [ADR 0006](../adr/0006-prototype-gates-workspace-browser-delivery.md).
- [Report lifecycle and trust rules](research-paper-workspace/closed/05-report-lifecycle-and-trust-rules.md)
  - Require approved outlines, immutable report/citation history, visible trust
    summaries, and user-controlled recovery rather than silent evidence change.
- [Single-user application topology](research-paper-workspace/closed/06-application-topology.md)
  - Use a React browser workspace over same-origin FastAPI APIs, SQLite plus
    managed local files, and a single-process durable operation executor.
- [Product acceptance and demonstration evidence](research-paper-workspace/closed/07-product-acceptance.md)
  - Validate traceability and citation-review behaviour with offline acceptance
    tests and a separate ten-paper open-access portfolio demonstration, never
    generic-RAG performance claims.
- [Prototype gates workspace browser delivery](../adr/0006-prototype-gates-workspace-browser-delivery.md)
  - Compare and accept a high-fidelity desktop Interaction Prototype and its
    Interaction Contract before unfinished browser-bearing delivery work.
- [Outline-query controlled retrieval](../adr/0007-outline-query-controlled-retrieval.md)
  - The accepted workspace has four stages. The Owner versions retrieval
    queries with the outline; Chapter Evidence Bundles are automatic and frozen
    per Report Operation Attempt rather than manually curated in a separate UI.

## Frontier

[08 Connect Preparation and Reading to the Accepted Workspace](../../.scratch/research-paper-workspace/issues/08-connect-preparation-and-reading-to-accepted-workspace.md)
is the current delivery frontier. Ticket 07 accepted the flow-driven desktop
architecture and its Interaction Contract; real browser delivery may now begin
from the import and paper-reading stages.

## Delivery status

- [01 Create a Research Workspace and Select Uploaded Papers](../../.scratch/research-paper-workspace/issues/01-create-workspace-upload-select-papers.md)
  is complete.
- [02 Discover and Import Open Research Papers](../../.scratch/research-paper-workspace/issues/02-discover-and-import-open-papers.md)
  is complete.
- [03 Prepare a Research Workspace in the Browser](../../.scratch/research-paper-workspace/issues/03-prepare-workspace-in-browser.md)
  is complete.
- [04 Generate, Edit, and Approve a Report Outline](../../.scratch/research-paper-workspace/issues/04-generate-edit-approve-report-outline.md)
  is complete.
- [04A Stabilize Workspace UX and Paper Discovery](../../.scratch/research-paper-workspace/issues/04a-stabilize-workspace-ux-and-discovery.md)
  is complete.
- [05 Generate and Edit a Cited Literature Report](../../.scratch/research-paper-workspace/issues/05-generate-edit-cited-literature-report.md)
  is complete as a cited-report structural shell, not as a real vector-RAG
  completion claim.
- [05A Index Ready Selected Paper Evidence](../../.scratch/research-paper-workspace/issues/05a-index-ready-selected-paper-evidence.md)
  is complete with provenance-aware Chunks, real provider embeddings,
  workspace-isolated FAISS indexes, and retryable indexing state.
- [06 Compare Desktop Workspace Candidates](../../.scratch/research-paper-workspace/issues/06-compare-desktop-workspace-candidates.md)
  is complete; the Workspace Owner selected an iterated flow-driven direction.
- [07 Accept the Complete Workspace Interaction Prototype](../../.scratch/research-paper-workspace/issues/07-accept-complete-workspace-interaction-prototype.md)
  is complete; its accepted Interaction Contract is the browser-acceptance
  source.
- [08 Connect Preparation and Reading to the Accepted Workspace](../../.scratch/research-paper-workspace/issues/08-connect-preparation-and-reading-to-accepted-workspace.md)
  is the current frontier.
- [09 Generate, Edit, and Approve an Evidence-Driven Outline](../../.scratch/research-paper-workspace/issues/09-generate-edit-approve-evidence-driven-outline.md)
  is blocked by 08.
- [10 Curate and Confirm Chapter Evidence](../../.scratch/research-paper-workspace/issues/10-curate-and-confirm-chapter-evidence.md)
  is blocked by 09.
- [11 Generate Verified Body Chapters](../../.scratch/research-paper-workspace/issues/11-generate-verified-body-chapters.md)
  is blocked by 10.
- [12 Publish an Editable Evidence-Driven Literature Report](../../.scratch/research-paper-workspace/issues/12-publish-editable-evidence-driven-report.md)
  is blocked by 11.
- [13 Inspect Claim Evidence and Open the Original PDF](../../.scratch/research-paper-workspace/issues/13-inspect-claim-evidence-and-original-pdf.md)
  is blocked by 12.
- [14 Review Direct Edits and AI Rewrites](../../.scratch/research-paper-workspace/issues/14-review-direct-edits-and-ai-rewrites.md)
  is blocked by 13.
- [15 Export Markdown and Demonstrate the Product Workflow](../../.scratch/research-paper-workspace/issues/15-export-and-demonstrate-product-workflow.md)
  is blocked by 14.

## Out of scope

- Multi-user accounts, collaboration, and shared workspaces.
- PDF and Word report export; Markdown export is sufficient for the first
  version.
- Paywalled-paper scraping or automatic import of restricted full text. Only
  open PDFs are auto-imported; users may upload authorised files.
