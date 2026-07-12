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

## Frontier

- [Define product acceptance and demonstration evidence](research-paper-workspace/07-product-acceptance.md)

## Not yet specified

- The product acceptance scenarios, demonstration corpus, and non-regression
  evaluation after the end-to-end workflow is specified.
- The migration sequence from the generic-RAG refactor roadmap to this product
  roadmap.

## Out of scope

- Multi-user accounts, collaboration, and shared workspaces.
- PDF and Word export; Markdown export is sufficient for the first version.
- Paywalled-paper scraping or automatic import of restricted full text. Only
  open PDFs are auto-imported; users may upload authorised files.
