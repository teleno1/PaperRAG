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
  -> read a ready paper in its authorised original PDF
  -> generate, edit, and approve an outline
  -> retrieve and curate chapter evidence from ready workspace papers
  -> generate an editable cited Literature Report from confirmed evidence
  -> inspect claim-level evidence and open its original PDF location
  -> edit claims, use validated AI rewrite proposals, and review, remove, or
     refresh affected citations
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
20. As a researcher, I want to select a cited Claim and see paper title, source location, and source excerpt in the task detail pane, so that I can verify the claim without manually searching every PDF.
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
31. As a researcher, I want a Selected Paper to become ready only after its current Document Version has been parsed, chunked, embedded, and indexed in my Research Workspace, so that report generation uses real paper evidence.
32. As a researcher, I want every Chunk used for retrieval to retain its paper, version, section, page range, character range, and clean excerpt, so that every Claim Citation can lead me back to a useful location.
33. As a researcher, I want the system to generate my Report Outline from representative evidence across my ready Selected Papers, so that the structure is informed by the papers rather than a fixed template.
34. As a researcher, I want an outline to contain ordered chapters and sections with objectives, expected claims, and retrieval queries, so that I can inspect and edit the plan that will drive generation.
35. As a researcher, I want the outline to have an abstract, body chapters, conclusion-and-outlook, and references as distinct roles, so that sections which do not require retrieval are never treated as ordinary evidence-generation tasks.
36. As a researcher, I want each body chapter to retrieve evidence from its sections' queries before it writes, so that the report is grounded at a useful writing unit without losing the detail of section-level intent.
37. As a researcher, I want body chapters without dependencies to generate concurrently, so that long reports do not unnecessarily wait chapter by chapter.
38. As a researcher, I want every generated factual Claim to name one or more retrieved Chunks, so that the system cannot attach an arbitrary or whole-report citation after writing.
39. As a researcher, I want an independent support check for every generated Claim, so that a source ID being in the retrieval result is not mistaken for evidence that actually supports the text.
40. As a researcher, I want unsupported content to appear as an explicit evidence gap, so that the report does not fill missing evidence with plausible but uncited prose.
41. As a researcher, I want conclusion claims to show which verified body Claims they derive from, so that synthesis retains traceability instead of inventing a new evidence path.
42. As a researcher, I want an uncited abstract that only compresses the verified report, so that the conventional abstract remains readable without becoming a source of new facts.
43. As a researcher, I want future-outlook content to retrieve and verify its own paper evidence, so that forward-looking factual statements remain inspectable.
44. As a researcher, I want the generated body Claims to remain unchanged during final assembly, so that automated polishing never silently invalidates verified citations.
45. As a researcher, I want a references chapter even when some selected papers are not cited in a Claim, so that the report clearly distinguishes papers consulted for this attempt from papers actually cited.
46. As a researcher, I want malformed model JSON to be repaired once or fail visibly, so that a permissive parser or a template fallback cannot disguise a failed model operation.
47. As a researcher, I want a failed generation to retain completed chapter work and retry only the failed chapter, so that I do not pay for or wait for successful evidence work again.
48. As a researcher, I want the browser to show chapter progress, safe errors, and retry actions, so that an external-provider failure is recoverable rather than an opaque failed page.
49. As a maintainer, I want every Report Operation Attempt to snapshot the outline, Evidence Coverage, model configuration, prompt versions, and chapter evidence bundles, so that retries and later provenance inspection use a stable input boundary.
50. As a maintainer, I want production generation to fail explicitly when its configured embedding or chat model is unavailable, so that test fakes, templates, or lexical retrieval cannot become a hidden production fallback.
51. As a portfolio reviewer, I want a manual run against real configured providers in addition to offline controlled tests, so that the product demonstrates an actual RAG workflow rather than only a simulated one.
52. As a researcher, I want every workspace stage to remain visible and explain its missing prerequisite with a direct next action, so that a necessary workflow control never disappears because I am early in the journey.
53. As a researcher, I want to read a Selected Paper in its authorised original PDF and open a cited page from a report Claim, so that paper reading is not replaced by reconstructed Chunk text.
54. As a researcher, I want unavailable historical PDF evidence to say so truthfully while retaining its historical citation metadata and recovery action, so that a broken source is not presented as a readable paper.
55. As a researcher, I want to inspect every chapter's outline queries and automatically retrieved candidates before writing, so that I can judge the evidence rather than accepting a hidden retrieval result.
56. As a researcher, I want to remove unsuitable candidate Chunks and manually search all ready Selected Papers to add useful Chunks, so that my body evidence reflects my research judgment.
57. As a researcher, I want to explicitly confirm a complete Evidence Curation Version before body generation, so that the report freezes the exact Chapter Evidence Bundles and Evidence Coverage I chose.
58. As a researcher, I want a cited report sentence to reveal an affordance on hover and remain highlighted when selected, so that I can inspect its sources without guessing which small marker is interactive.
59. As a researcher, I want the writing area to default to report preview and enter editing only through an explicit control, so that ordinary reading does not accidentally alter my Report Draft.
60. As a researcher, I want an AI Rewrite Proposal to be support-checked against my current sources before I apply it, so that assistant-written changes do not silently weaken citation trust.
61. As a Workspace Owner, I want to compare at least three complete desktop interaction architectures using the same scenario, so that I can choose or iterate toward an experience I actually find usable.
62. As a Workspace Owner, I want the selected prototype to expose every normal, failure, and recovery state together with a control inventory, so that later delivery cannot omit necessary buttons or states.
63. As a maintainer, I want the prototype and production browser to use the same Workspace View State contract, so that prototype acceptance tests map to real user-visible product behaviour rather than a separate mock-only design.

## Implementation Decisions

- **Evidence-driven report-generation contract.** Use Alibaba Cloud
  `text-embedding-v4` for both Chunk and query embeddings, and
  `deepseek-v4-flash` for outline planning, body generation, support checking,
  and final synthesis. Keys are read only from local `DASHSCOPE_API_KEY` and
  `DEEPSEEK_API_KEY` environment variables. A Report Operation Attempt records
  provider, model, role parameters, and prompt-template version, never a key.
  Missing configuration, provider failure, malformed output after repair, or a
  retrieval/index failure is a safe retryable operation failure: it must never
  fall back silently to lexical retrieval, a fixed outline, or templated prose.
- **Chunk and index boundary.** Chunk only within parsed title/section
  boundaries, at roughly 500 tokens with two complete-sentence overlap and
  Chinese/English sentence detection. Persist the Research Paper, Document
  Version, Chunk, section, page start/end, character start/end, and clean
  excerpt. Do not independently embed tables or formulas in the first version.
  Index only ready current Document Versions in a Research Workspace-isolated
  FAISS index carrying this metadata.
- **Planning retrieval and outline schema.** Build a Planning Evidence Bundle
  from three to five topic-and-question queries. Retrieve vector candidates,
  deduplicate and MMR-rerank them across papers, and supply roughly 12–20
  representative Chunks with at most two from each paper to the outline model.
  The fixed prompt separates system grounding/JSON rules, task context,
  bounded planning evidence, and JSON Schema. The response contains ordered
  chapter roles: exactly one first abstract, one or more body chapters, one
  conclusion-and-outlook chapter, and one final references chapter. Body
  sections contain a title, objective, expected claims, and at least one query;
  conclusion-and-outlook may contain outlook queries; abstract and references
  contain none. The service assigns identities, ordering, revisions, and
  snapshots. Regeneration takes a user instruction and returns a complete
  replacement outline.
- **Body-chapter retrieval and generation.** Each body-section query retrieves
  eight vector candidates. Deduplicate their union per chapter and MMR-rerank
  to a Chapter Evidence Bundle of 12–18 Chunks, at most three per paper,
  retaining section/query attribution and similarity scores. Do not initially
  use an arbitrary score cutoff as a support decision; calibrate any later
  threshold from real demonstration results. A section with no candidates
  becomes an evidence-gap block without an LLM call; a wholly empty chapter is
  an all-gap result. A fixed body prompt receives grounding/JSON rules,
  report/chapter/section context, the bounded bundle, and output Schema. It
  emits ordered section blocks: one independently editable sentence or bullet
  Claim with proposed Chunk IDs, or an evidence-gap block with a reason.
- **Evidence curation before body generation.** Chapter queries retrieve from
  every ready Selected Paper in the workspace. In the evidence-retrieval stage,
  the owner can inspect the candidates, remove a Chunk, search any ready
  workspace paper, and add an eligible Chunk. The saved Evidence Curation
  Version records those choices per chapter. A single explicit confirmation
  requires every body chapter to be curated or marked as an evidence gap,
  establishes Evidence Coverage from the papers actually represented, and
  freezes the version before eligible body chapters run in parallel.
- **Generation DAG and final synthesis.** Body chapters are independent and
  run with deployment-configurable bounded parallelism (default two chapter
  workers). Within a chapter, retrieval, generation, support checking and its
  one possible regeneration are serial. Conclusion-and-outlook waits for body
  chapters; conclusion entries contain `derived_from_claim_ids` and inherit
  their source evidence, while outlook entries use their own retrieved and
  validated Chunks. Abstract waits for the completed report, has no retrieval
  or visible citations, and may only compress existing verified Claims while
  retaining internal derived-Claim links. Final synthesis does not rewrite,
  reorder, or polish body Claims. References do not enter a model prompt.
- **Support and JSON validation.** Validate every output against its declared
  JSON Schema. On the first parse or schema failure, send the validation error
  to the same role for one repair; a second failure fails the phase. Validate
  generated Claim IDs against the Chapter Evidence Bundle, then batch a
  chapter's support checks while limiting each check to its Claim and proposed
  Chunks. Only `supported` creates a verified Claim Citation. A
  `partially_supported` or `unsupported` Claim gets one regeneration using the
  reason and a second check; remaining failures become explicit evidence gaps.
  Conclusion inherited sources receive the same support check.
- **Publication, retry, and references.** An Attempt freezes its approved
  Outline Revision, confirmed Evidence Curation Version and derived Evidence
  Coverage, model/prompt configuration, and Chapter Evidence Bundles. Persist
  ChapterRuns, normalized evidence bundles, Claim
  candidates, validation verdicts, retry counts, and safe errors; never store
  raw prompts, complete paper content, or credentials in operation history.
  Completed chapters remain in a failed Attempt. Retry reruns only failed
  chapters and downstream dependencies; user regeneration creates a new
  Attempt. Publish a new Report Draft only after every required chapter reaches
  a valid cited result or applicable evidence gap. Render the references chapter
  deterministically from ready Evidence Coverage: every paper is marked cited
  or consulted-but-uncited; only cited papers have body citation markers.
  Use first-appearance `[n]` numbering, GB/T 7714 field order for Chinese, the
  corresponding numbered English rendering for English, and omit unavailable
  bibliographic fields rather than inventing them.

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
  chunking versions. A Paper Reading View renders the authorised original PDF,
  and a Claim Citation opens it at the anchored page with a location cue. It
  must never reconstruct paper reading from Chunks; annotation, note-taking,
  PDF editing, and pixel-level text highlighting remain out of scope.
- Generate the Report Outline separately from the Literature Report. The report
  generator consumes the approved current outline, workspace topic, Report
  Language, and only workspace-scoped retrieved sources. A draft outline needs
  explicit user approval before evidence curation and body generation. Outline
  planning may use ready Selected Papers, but the final body evidence is chosen
  only in the evidence-retrieval stage; its confirmed Evidence Curation Version
  derives Evidence Coverage. No report body is generated without ready evidence.
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
  conclusion: a body chapter may complete with validated cited Claims and/or
  explicit section evidence gaps, but a new Report Draft is published only
  after every required chapter and dependency has completed. A report displays
  a Report Trust Summary with Evidence Coverage, citation-state counts, and gap
  notes; gaps, pending review, and evidence-unavailable citations mark it as
  needing attention without blocking Markdown export.
- Detect substantive changes to a cited claim at the report-edit boundary.
  Presentation-only edits preserve its Citation Review State; any change to
  normalized visible Claim text moves all attached citations to pending review,
  except an AI Rewrite Proposal that passes the same source-bounded support
  check before the user applies it. The user can confirm (which becomes
  user-confirmed), remove, or refresh the citation, but only successful
  workspace-scoped validation or refresh restores verified. A rewrite proposal
  that is partially supported or unsupported displays its reason and cannot
  automatically overwrite the draft. A refresh records its Evidence Coverage,
  creates a successor Citation Revision only on valid support, and otherwise
  leaves the citation pending review with a no-support result. A citation whose
  paper was removed or whose Document Version was replaced is
  evidence-unavailable and cannot be verified, even when its old revision
  contains other active sources.
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
- **Prototype gate and Workspace View State.** Before unfinished
  browser-bearing delivery work starts, build an isolated high-fidelity desktop
  Interaction Prototype over a single Workspace View State contract. Its
  fixture adapter and scenario switcher simulate the same visible states that
  the production API adapter will later provide; neither reproduces domain
  logic. Compare at least three complete normal-journey architectures with one
  shared visual baseline, then iterate a selected or hybrid direction until the
  Workspace Owner accepts the complete Interaction Contract. The first
  candidate is a five-stage workspace (import, paper reading, outline,
  evidence curation, writing) with left stage navigation, central task surface,
  and a stage-specific right Task Detail Pane. Every stage remains visible and
  explains unavailable prerequisites with a direct next action. Only desktop
  browsers are in scope.
- **Report and evidence interaction.** A cited Claim gives its sentence area a
  hover affordance and remains highlighted when selected. The Task Detail Pane
  then shows all source excerpts, provenance, location, and trust state; a
  source opens the original-PDF Paper Reading View at its anchor. The writing
  stage defaults to report preview and enters editing through an explicit
  control. Preview shows evidence and trust summary; editing additionally
  exposes a source-bounded AI Rewrite Proposal assistant for a selected Claim
  or passage. Draft changes auto-save with visible status; an explicit save
  creates an immutable Report Revision.
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

- Extend the existing `ResearchWorkspace` application seam rather than adding
  a parallel report-generation stack. Inject deterministic embedding, vector
  retrieval, planning, body-generation, support-check, and synthesis
  collaborators to test observable state, provenance, and retry behavior.
- Add contract tests for every JSON role: accepted schema, one repair after an
  invalid result, and a visible failed operation after the second invalid
  result. Verify that no production path silently substitutes a template or
  lexical retriever when a real-model collaborator is unavailable.
- Add retrieval and orchestration tests for section-query attribution, eight
  candidates per query, chapter-level deduplication/MMR limits, workspace and
  document-version isolation, all-gap sections/chapters, two-worker scheduling,
  and dependency ordering from body chapters through conclusion/outlook,
  abstract, and references.
- Add report-contract tests for one-to-many Claim Citations, support verdict
  handling, one regeneration only, derived conclusion citations, uncited but
  internally derived abstracts, independently grounded outlook Claims,
  unchanged verified body Claims, and deterministic references that include
  both cited and consulted-but-uncited papers.
- Add Evidence Curation Version tests for chapter-query candidates from all
  ready Selected Papers, Chunk removal and manual addition, explicit global
  confirmation, evidence-gap chapters, derived Evidence Coverage, frozen
  attempt inputs, and isolation from later curation changes.
- Add failure/recovery tests that freeze Attempt inputs, preserve completed
  ChapterRuns, retry only failed chapters and downstream work, never publish a
  partial Report Draft, and preserve the previous draft after failure.
- Offline tests may use controlled collaborators but cannot close a delivery
  ticket on their own. Each model-backed ticket requires a documented manual
  acceptance run using the configured `text-embedding-v4` and
  `deepseek-v4-flash` providers, with no keys or generated artifacts committed.

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
  from substantive direct edits and verified AI Rewrite Proposals, and verify
  their Citation Review States, validation reasons, and available resolution
  actions.
- Add lifecycle tests for Evidence Curation-derived Evidence Coverage, outline
  approval/out-of-sync reports, non-destructive regeneration,
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
- First test the isolated Interaction Prototype through the Workspace View
  State fixture seam: every candidate completes the normal journey, and the
  selected architecture covers the full Prototype Journey Boundary, every
  operation/recovery state, its control inventory, and comparison feedback.
  Then apply the accepted Interaction Contract to production browser acceptance
  tests. Cover the five-stage workspace, original-PDF reading from a Claim,
  evidence curation, a multi-source Claim, a pending-review direct edit, and a
  validated AI rewrite.
- Preserve existing parser, retrieval, report, citation-validation, health, and
  state tests as regression coverage. The legacy generic-evaluation fixtures
  may continue as low-level regression assets but do not serve as the product's
  primary acceptance evidence.
- Product acceptance uses four deterministic browser scenarios: cited report
  generation, multi-source evidence inspection, Claim-edit review/refresh, and
  partial-readiness or removed-evidence handling with transparent Markdown
  export. All visible citations must resolve to same-workspace, same-version
  SourceAnchors; ineligible evidence may not remain verified; substantive
  direct edits must enter pending review; and persisted
  workspace/report/citation/operation state must survive browser reload and
  service restart.
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
- PDF annotation, personal notes, PDF editing, or pixel-level source
  highlighting; the original-PDF Paper Reading View and page-level citation
  jump are in scope
- mobile or narrow-screen workspace layouts
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
- The Interaction Prototype is the active delivery frontier. Its accepted
  Interaction Contract is the source of truth for subsequent browser behaviour;
  local delivery tickets declare the resulting implementation order and
  verification.
- The local Wayfinder map replaces GitHub Issues for this effort because the
  repository's GitHub integration lacks permission to create issues.
