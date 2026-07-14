# Wayfinder: Research-Paper Workspace Product Direction

> Local tracker fallback. GitHub Issues is the configured tracker, but its
> connected integration does not have permission to create issues in this
> repository. This document and its linked local tickets are the canonical
> planning map until GitHub write access becomes available.

## Destination

Define an implementation-ready product specification and delivery route for
PaperRAG as a single-user research-paper workspace: users set a topic, upload
or discover and select papers, generate an editable literature report, and
trace each cited claim to one or more paper chunks in the web interface.

## Notes

- Product focus: individual researchers and graduate students, not a
  general-purpose RAG platform.
- Use `$grilling` and `$domain-modeling` for user-facing or domain decisions;
  use `$prototype` for interaction decisions.
- This map is planning-only. It ends when the implementation route and
  acceptance criteria are clear; it does not itself implement the product.
- The current synthesised specification is [Research-Paper Workspace](../specs/research-paper-workspace.md).
  It is refined as open tickets resolve.
- A ticket is open until its decision is recorded in the ticket. Resolved local
  tickets are moved to `research-paper-workspace/closed/` and indexed here.
- An open ticket is on the frontier only when it has no open `Blocked by`
  ticket. Tickets are claimed locally by adding `Claimed by` before work begins.

## Decisions so far

- [First-version product boundary](research-paper-workspace/closed/00-first-version-product-boundary.md)
  — A single-user, browser-based literature-report workspace with selected
  papers as its only evidence, claim-level provenance, and Markdown export.
- [Research open-paper discovery and import adapters](research-paper-workspace/closed/03-paper-discovery-research.md)
  — Use OpenAlex for topic discovery, arXiv for direct selected-paper import,
  and a guarded OpenAlex OA-PDF fallback; only a verified PDF becomes evidence.
- [Audit stable PDF source-location anchors](research-paper-workspace/closed/04-pdf-location-anchor-audit.md)
  — Propagate a versioned `SourceAnchor` with page range, section, and clean
  excerpt through chunks, retrieval, and persisted claim citations.
- [Research Workspace and provenance contract](research-paper-workspace/closed/01-workspace-provenance-contract.md)
  - Use immutable workspace-scoped identities and revision snapshots; only a
    ready Selected Paper's active Document Version may be new evidence.
- [Report editor and evidence-trace interaction](research-paper-workspace/closed/02-evidence-trace-prototype.md)
  - Use the guided-workspace layout: paper boundary at left, editable report
  and approved outline at centre, and a persistent claim-evidence panel at
  right.
- [Report lifecycle and trust rules](research-paper-workspace/closed/05-report-lifecycle-and-trust-rules.md)
  - Require approved outlines, explicit ready-subset generation, immutable
  report/citation history, visible trust summaries, and user-controlled
  recovery rather than silent evidence changes.
- [Single-user application topology](research-paper-workspace/closed/06-application-topology.md)
  - Use a React browser workspace over same-origin FastAPI APIs, SQLite plus
  managed local files, and a single-process durable operation executor.
- [Product acceptance and demonstration evidence](research-paper-workspace/closed/07-product-acceptance.md)
  - Validate traceability and citation-review behavior with offline acceptance
  tests and a separate 10-paper OA portfolio demonstration, never generic-RAG
  performance claims.

## Frontier

No open planning tickets. The implementation route and acceptance contract are
ready for the local delivery tickets in `.scratch/research-paper-workspace/issues/`.

## Delivery status

- [01 — Create a Research Workspace and Select Uploaded Papers](../../.scratch/research-paper-workspace/issues/01-create-workspace-upload-select-papers.md)
  is complete.
- [02 Discover and Import Open Research Papers](../../.scratch/research-paper-workspace/issues/02-discover-and-import-open-papers.md)
  is complete.
- [03 Prepare a Research Workspace in the Browser](../../.scratch/research-paper-workspace/issues/03-prepare-workspace-in-browser.md)
  is complete.
- [04 Generate, Edit, and Approve a Report Outline](../../.scratch/research-paper-workspace/issues/04-generate-edit-approve-report-outline.md)
  is complete.
- [04A Stabilize Workspace UX and Paper Discovery](../../.scratch/research-paper-workspace/issues/04a-stabilize-workspace-ux-and-discovery.md)
  is complete and is the stabilization checkpoint for the browser workspace.
- [05 Generate and Edit a Cited Literature Report](../../.scratch/research-paper-workspace/issues/05-generate-edit-cited-literature-report.md)
  is complete. Tickets 06–08 use a minimal functional
  interface while final workspace UX is deliberately deferred. This historical
  completion is only the cited-report structural shell; tickets 05A through 05D below define
  the real vector-RAG workflow now required before ticket 06.
- [05A Index Ready Selected Paper Evidence](../../.scratch/research-paper-workspace/issues/05a-index-ready-selected-paper-evidence.md)
  is complete. It delivers provenance-aware chunks, real provider embeddings,
  workspace-isolated FAISS indexes, and retryable indexing state.
- [05B Generate an Evidence-Driven Report Outline](../../.scratch/research-paper-workspace/issues/05b-generate-evidence-driven-report-outline.md)
  is the current delivery frontier and is unblocked by 05A.
- [05C Generate Verified Body Chapters](../../.scratch/research-paper-workspace/issues/05c-generate-verified-body-chapters.md)
  is blocked by 05B.
- [05D Publish a Complete Evidence-Driven Literature Report](../../.scratch/research-paper-workspace/issues/05d-publish-complete-evidence-driven-literature-report.md)
  is blocked by 05C.
- [06 Inspect Claim Evidence and Multiple Sources](../../.scratch/research-paper-workspace/issues/06-inspect-claim-evidence-and-multiple-sources.md)
  is blocked by 05D.
- [07 Review and Refresh Edited Claim Citations](../../.scratch/research-paper-workspace/issues/07-review-refresh-edited-claim-citations.md)
  is blocked by 06.
- [08 Export Markdown and Demonstrate the Product Workflow](../../.scratch/research-paper-workspace/issues/08-export-and-acceptance-demo.md)
  is blocked by 07.
- [09 Prototype the Final Research Workspace Experience](../../.scratch/research-paper-workspace/issues/09-prototype-final-research-workspace-experience.md)
  is blocked by 08 and is a disposable prototype decision ticket.
- [10 Implement the Accepted Research Workspace Prototype](../../.scratch/research-paper-workspace/issues/10-implement-accepted-workspace-prototype.md)
  is blocked by 09 and reconnects the accepted prototype to the real product.

## Not yet specified

- The migration sequence from the generic-RAG refactor roadmap to this product
  roadmap is a follow-on compatibility concern, not a blocker for workspace
  implementation.

## Out of scope

- Multi-user accounts, collaboration, and shared workspaces.
- PDF and Word export; Markdown export is sufficient for the first version.
- Paywalled-paper scraping or automatic import of restricted full text. Only
  open PDFs are auto-imported; users may upload authorised files.
