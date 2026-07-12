---
status: ready-for-agent
tracker: local-fallback
---

# Spec: Research-Paper Workspace

## Problem Statement

Researchers and graduate students often read papers across disconnected tools:
search sites, local PDF folders, notes, and a separate writing surface. Generic
RAG demos can produce text with source IDs, but they do not give the user a
bounded paper set, a controlled literature-writing workflow, or a practical way
to inspect which exact paper content supports a report claim.

PaperRAG will provide one single-user Research Workspace for a topic. The user
adds papers by upload or open-paper discovery, explicitly selects the evidence
set, approves an outline, and edits a Literature Report. Each supported claim
in the report exposes one or more Claim Citations. Selecting a citation reveals
the supporting Research Paper and Source Chunk, including a source location and
excerpt. When the user substantively changes a cited claim, its citation becomes
pending review rather than continuing to appear verified.

## Solution

The product is a browser-based, single-user research-paper workspace with this
workflow:

```text
create workspace with topic and report language
  -> upload papers or search open academic indexes
  -> select the papers that may serve as evidence
  -> process selected papers and show readiness
  -> generate, edit, and approve an outline
  -> generate an editable cited Literature Report
  -> inspect claim-level evidence in a side panel
  -> edit claims and review, remove, or refresh affected citations
  -> export Markdown
```

The existing parser, chunking, vector index, retrieval, report generation, and
source-validation capabilities are reused behind the workspace. The product
does not claim that a small generic evaluation corpus demonstrates enterprise
RAG performance; product trust is expressed through visible provenance,
explicit citation-review state, and repeatable end-to-end acceptance scenarios.

## User Stories

1. As an individual researcher, I want to create a Research Workspace with a topic, so that all papers and reports for one literature task stay bounded together.
2. As a graduate student, I want to choose Chinese or English for a workspace, so that the report matches my intended audience even when papers are in another language.
3. As a researcher, I want to upload an authorised PDF directly, so that a paper I already possess can become evidence without depending on an external index.
4. As a researcher, I want to search open academic sources by topic, so that I can discover Candidate Papers without leaving the workspace.
5. As a researcher, I want Candidate Papers to show title, authors, abstract or summary when available, year, venue, and source link, so that I can judge whether to include them.
6. As a researcher, I want the system to distinguish a Candidate Paper from a Selected Paper, so that unreviewed search results never silently influence my report.
7. As a researcher, I want the system to import only publicly downloadable PDFs automatically, so that paper discovery respects access and copyright boundaries.
8. As a researcher, I want a restricted or unavailable Candidate Paper to remain visible with its link and import status, so that I know why it is not evidence and can upload an authorised copy if appropriate.
9. As a researcher, I want to select and remove papers from the workspace, so that I can control the exact evidence boundary before drafting.
10. As a researcher, I want to see each Selected Paper's processing state, so that I know whether it is ready for retrieval or needs attention.
11. As a researcher, I want failed imports and parsing failures to identify the affected paper and a recoverable next action, so that one bad PDF does not obscure the rest of my workspace.
12. As a researcher, I want the workspace to preserve paper metadata and source provenance, so that I can later understand where every paper entered the project.
13. As a researcher, I want an editable Report Outline before long-form drafting, so that I can steer the literature review structure instead of repairing a one-shot report.
14. As a researcher, I want the default outline to cover research question, methods and findings, comparison, limitations or research gaps, conclusion, and references, so that I begin from a useful review structure.
15. As a researcher, I want to add, remove, rename, and reorder outline sections, so that the report follows my actual research question.
16. As a researcher, I want report generation to use only Selected Papers, so that generated claims stay within the evidence set I reviewed.
17. As a researcher, I want to edit the generated Literature Report in the browser, so that the final writing remains mine.
18. As a researcher, I want a supported report sentence or bullet to display a citation marker, so that I can distinguish sourced content from unsourced notes or edits.
19. As a researcher, I want one report claim to cite multiple Source Chunks when necessary, so that synthesis across papers is transparent rather than reduced to a single token citation.
20. As a researcher, I want to select a citation marker and see paper title, source location, and source excerpt in a side panel, so that I can verify the claim without manually searching every PDF.
21. As a researcher, I want page and/or section information to be shown whenever parsing provides it, so that I can locate evidence in the original paper.
22. As a researcher, I want citations to retain a verified state only while they support the displayed claim, so that the interface does not overstate trust after editing.
23. As a researcher, I want a substantive edit to mark affected citations pending review, so that I can deliberately decide whether their evidence still applies.
24. As a researcher, I want to keep, remove, or refresh a pending citation, so that I can resolve evidence status without abandoning my edits.
25. As a researcher, I want citation refresh to retrieve only from the same workspace's Selected Papers, so that a refreshed citation cannot cross the evidence boundary.
26. As a researcher, I want unavailable or removed evidence to be clearly reflected in the report's citation state, so that I do not export a report that appears better grounded than it is.
27. As a researcher, I want to export the current report as Markdown, so that I can continue writing or submit the work in other tools.
28. As a researcher, I want the workspace to preserve report and citation provenance across browser refreshes, so that a long-running literature task is not an ephemeral demo.
29. As a portfolio reviewer, I want to see a coherent end-to-end workflow with visible evidence tracing, so that the project demonstrates product judgment rather than only benchmark metrics.
30. As a maintainer, I want external paper discovery, parsing, retrieval, and LLM generation to be replaceable in tests, so that product behavior can be verified without paid APIs or network access.

## Implementation Decisions

- Introduce `ResearchWorkspace` as the product-level application seam. It owns
  the workspace lifecycle and composes existing ingestion, indexing, outline,
  report-generation, retrieval, and source-validation capabilities rather than
  duplicating their logic in the web application.
- Persist a workspace-scoped model for topic, Report Language, Candidate Papers,
  Selected Papers, processing/index readiness, outlines, report versions,
  claims, Claim Citations, and Citation Review State. Each persisted entity has
  an opaque stable identifier, and every evidence relationship is constrained
  to its Research Workspace. Provider IDs, DOI/arXiv IDs, URLs, and hashes are
  provenance/deduplication attributes, not workspace identity.
- Keep `Document` and `DocumentChunk` as reusable underlying abstractions. A
  Research Paper is a specialised Document with scholarly metadata and
  provenance appropriate for the user interface.
- Treat selection as an evidence gate: Candidate Papers cannot be parsed,
  indexed, retrieved, cited, or passed to generation until they become Selected
  Papers. Direct uploads become Selected Papers after successful workspace
  registration.
- Implement Paper Discovery behind an adapter interface. OpenAlex is the
  first-version topic-search provider; arXiv is the first direct-import
  provider for user-selected e-prints; a verified OpenAlex OA PDF URL is a
  guarded fallback. Missing, restricted, duplicate, rate-limited, and non-PDF
  results require explicit statuses rather than silent fallback behavior.
- Propagate a versioned `SourceAnchor` through parsing, chunks, retrieval, and
  persisted Claim Citations. It captures document version, source reference,
  optional inclusive page range, nearest section, clean excerpt, and parser and
  chunking versions. Full PDF viewer highlighting is not required for the first
  version.
- Generate the Report Outline separately from the Literature Report. The report
  generator consumes the approved current outline, workspace topic, Report
  Language, and only workspace-scoped retrieved sources. A draft outline needs
  explicit user approval before body generation. If Selected Papers have mixed
  readiness, generation requires the user's explicit choice to use the ready
  subset and records the included and excluded papers as Evidence Coverage;
  no report body is generated without ready evidence.
- Represent the report as structured content containing stable claim identity
  and one-to-many Claim Citations, then render it into the browser editor and
  Markdown. Do not use a flat generated string as the authoritative report
  model. Save immutable outline/report revisions; Claims retain identity across
  ordinary edits, while splits and merges create new Claims. A Claim Citation
  retains immutable Citation Revisions containing its source-anchor snapshots;
  refresh adds a successor instead of rewriting prior evidence.
- Keep source-ID validation as a hard guard: generation and refresh may only
  retain citations present in the retrieved source registry for that operation.
- Treat missing support as a visible evidence gap, not an uncited factual
  conclusion: generation may complete supported outline sections while marking
  an unsupported section as needing more evidence. A report displays a Report
  Trust Summary with Evidence Coverage, citation-state counts, and gap notes;
  gaps, pending review, and evidence-unavailable citations mark it as needing
  attention without blocking Markdown export.
- Detect substantive changes to a cited claim at the report-edit boundary.
  Presentation-only edits preserve its Citation Review State; any change to
  normalized visible Claim text moves all attached citations to pending review.
  The user can confirm (which becomes user-confirmed), remove, or refresh the
  citation, but only successful workspace-scoped refresh restores verified. A
  refresh records its Evidence Coverage, creates a successor Citation Revision
  only on valid support, and otherwise leaves the citation pending review with
  a no-support result. A citation whose paper was removed or whose Document
  Version was replaced is evidence-unavailable and cannot be verified, even
  when its old revision contains other active sources.
- A Selected Paper is eligible for new evidence only while it is active and its
  current Document Version is ready. Track readiness as
  awaiting-authorised-file, importing, parsing, indexing, ready, failed, or
  unavailable, including a retryable failure phase. Reprocess into a new
  Document Version and switch atomically only after it is ready; preserve the
  predecessor and its historical source anchors.
- A workspace moves through setup, active, and archived states. Archiving is
  read-only and preserves provenance until the workspace is restored. A report
  remembers the Outline Revision used to generate it; a later outline change
  leaves it traceable but out of sync rather than invalidating its citations.
  Earlier saved report revisions remain exportable and can seed a new revision,
  but are not used for new retrieval or citation refresh.
- Persist the current Report Draft automatically across browser refreshes; only
  an explicit save creates an immutable Report Revision. Regeneration creates
  a separate persisted draft which the user must select before it becomes
  current. Failed generation or refresh records a phase and input snapshot for
  retry, never overwrites current content or evidence, and cannot turn partial
  streamed output into Claims or citations.
- Provide thin workspace-oriented API operations and progress/state surfaces.
  New browser contracts are versioned JSON endpoints under `/api/workspaces/...`
  and `/api/operations/{id}`; they expose product state and evidence, never
  filesystem paths or vector/provider internals. Existing generic API and CLI
  commands remain compatibility surfaces until deliberately adapted.
- The browser application calls workspace use cases through API contracts. It
  renders state and handles interactions but does not own parsing, retrieval,
  provenance, or citation-validation business rules. It is a React + TypeScript
  single-page application, separately runnable for development and served as
  compiled static assets by FastAPI in production.
- Default to a guided workspace composition: show topic and paper selection at
  left, the approved outline and editable Literature Report at centre, and a
  persistent evidence panel at right. Citation markers attach to individual
  Claims and open all their cited Source Chunks, including paper title,
  page/section where available, clean excerpt, Citation Revision, and visible
  evidence-readiness state. A content edit exposes pending-review resolution
  actions in place; the browser does not make a support decision itself.
- Use SQLite, through infrastructure repository adapters built on `sqlite3`, as
  the authoritative store for workspace metadata, provenance, revisions,
  citation state, and Workspace Operations. Keep PDFs, parsed artifacts, and
  workspace/version-scoped FAISS indexes under one configurable local data
  directory; do not add an ORM, database service, or cloud dependency.
- Run imports, parsing, indexing, generation, and citation refresh through an
  in-process durable Workspace Operation executor. Submission returns an
  operation ID; the browser polls persisted phase/progress/error state and
  retry actions. State-changing work is serialized per workspace and globally
  bounded. Queued operations may be cancelled; running work is never forcibly
  interrupted. A process restart marks unfinished work interrupted and
  retryable, without accepting partial stream output as report content.
- Package the first version as one native Python/FastAPI process and one
  Uvicorn worker, serving the same-origin compiled frontend and API on
  `127.0.0.1` by default. Docker/Compose, built-in authentication, public
  exposure, multi-worker execution, replicas, and automated backup are outside
  the first-version deployment boundary. Backup is a documented stopped-service
  copy of the configured data directory.

## Testing Decisions

- The primary test seam is the ResearchWorkspace application seam. Tests should
  observe externally meaningful transitions—paper selection, readiness, outline
  approval, report generation, claim citation inspection, edit invalidation,
  citation refresh, and Markdown export—rather than private implementation
  methods.
- Reuse the repository's existing fake-based use-case testing style for parser,
  retrieval, vector-store, and LLM collaborators. Unit and integration tests
  must not require paid APIs, external paper discovery, or a live PDF service.
- Add domain tests for evidence-gate invariants: an unselected Candidate Paper
  cannot enter indexing, retrieval, or a Claim Citation; a citation must point
  to a Source Chunk within the same workspace; and a removed or unavailable
  source cannot remain verified.
- Add report-editing tests that distinguish non-substantive presentation edits
  from substantive claim edits, and verify the resulting Citation Review State
  and available resolution actions.
- Add lifecycle tests for explicit ready-subset generation and Evidence
  Coverage, outline approval/out-of-sync reports, non-destructive regeneration,
  no-support evidence gaps, failed-operation retry, source/version removal,
  report trust summaries, and Markdown export of unresolved citation states.
- Add API-level tests for the workspace's user-visible state and error contract,
  including partial processing failure, unavailable public PDF, empty selected
  set, no retrieved support, and citation refresh that finds no valid evidence.
- Add topology tests for SQLite-backed restart persistence, workspace-operation
  serialization and queued cancellation, interrupted-operation recovery,
  polling status contracts, and same-origin static-frontend/API delivery. Use
  a single-worker test configuration; do not require a queue, database server,
  Docker, or network service.
- Add browser-level acceptance tests once the prototype decides the interaction.
  Cover the full workflow and the evidence side panel, including a claim with
  multiple citations and a pending-review claim after editing.
- Preserve existing parser, retrieval, report, citation-validation, health, and
  state tests as regression coverage. The legacy generic-evaluation fixtures
  may continue as low-level regression assets but do not serve as the product's
  primary acceptance evidence.
- Product acceptance uses four deterministic browser scenarios: cited report
  generation, multi-source evidence inspection, Claim-edit review/refresh, and
  partial-readiness or removed-evidence handling with transparent Markdown
  export. All visible citations must resolve to same-workspace, same-version
  SourceAnchors; ineligible evidence may not remain verified; substantive edits
  must enter pending review; and persisted workspace/report/citation/operation
  state must survive browser reload and service restart.
- Keep automated acceptance offline with controlled parser, discovery,
  retrieval, and LLM collaborators. The separate manual portfolio demonstration
  uses a frozen 10-paper open-access RAG-attribution manifest and an isolated
  data directory. Its preflight validates every versioned PDF, URL, hash, and
  provenance record; it fails rather than silently using fewer papers. The
  resulting Chinese report selects all 10 papers, contains at least eight cited
  Claims across at least six papers, has at least two multi-source Claims, and
  visibly demonstrates one evidence gap or controlled exception. These gates
  demonstrate workflow and provenance, not enterprise performance or answer
  accuracy from a small corpus.

## Out of Scope

- multi-user accounts, authentication, collaboration, or shared workspaces
- scraping paywalled papers or automatically importing restricted full text
- PDF or Word report export; Markdown is the first-version export
- a complete PDF reader or pixel-level source highlighting
- runtime behavior driven by offline gold labels or the legacy evaluation set
- claims that the legacy 14-document evaluation corpus represents enterprise
  scale or validates the new product workflow
- replacing every existing CLI/API compatibility surface before the workspace
  flow has a tested replacement

## Further Notes

- This specification is the synthesised baseline for the product direction. It
  is intentionally explicit about unresolved implementation choices so that
  they are decided through the active local Wayfinder tickets rather than hidden
  in implementation.
- Wayfinder planning is complete. The local delivery tickets are the source of
  truth for implementation order and verification.
- The local Wayfinder map replaces GitHub Issues for this effort because the
  repository's GitHub integration lacks permission to create issues.
