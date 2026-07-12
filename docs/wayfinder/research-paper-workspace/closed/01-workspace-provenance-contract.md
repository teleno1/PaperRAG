---
type: grilling
status: closed
claimed_by: Codex
blocked_by: []
resolved: 2026-07-12
---

# Model the Research Workspace and Provenance Contract

## Question

What persistent entities, identifiers, state transitions, and invariants are
required for a Research Workspace to preserve a Claim Citation from report
text through selected paper, parsed unit, and source chunk?

The decision must cover workspace creation, paper selection/removal,
parsing/index readiness, report and outline versions, claim identity, citation
review states, and what becomes invalid after paper or report changes.

## Decision log

- **2026-07-11 — selected-paper removal:** A user may remove a Selected Paper
  even when a report cites it. The workspace retains the historical selection
  and provenance records, but the paper leaves the active evidence boundary;
  dependent citations become evidence-unavailable and cannot remain verified.
- **2026-07-11 — outline and report revisions:** The current editable outline
  and Literature Report form immutable revisions on save, generation, or
  approval. A Claim Citation records the report revision in which it was made;
  older revisions remain traceable but cannot be used for current retrieval,
  or citation refresh; they remain exportable.
- **2026-07-11 — claim edits and citation review:** The system automatically
  preserves citations for presentation-only edits, but makes every
  content-changing claim citation pending review. It does not declare a
  changed claim supported. The user may confirm the citation after inspecting
  its evidence, remove it, or refresh it. Only a successful refresh from the
  current workspace's Selected Papers restores verified; an unavailable source
  cannot be verified.
- **2026-07-11 — document-version replacement and reprocessing:** Every
  replacement or reprocessing run creates a new immutable Document Version.
  A ready predecessor remains the active evidence version until its successor
  is fully parsed, indexed, and ready. The successor then becomes active
  atomically; current-report citations to the predecessor become pending
  review, while historical reports retain their source-anchor snapshots. A
  failed successor leaves the predecessor usable.
- **2026-07-11 — workspace lifecycle:** A Research Workspace moves from setup
  to active and may then be archived. An archived workspace is read-only and
  cannot process, retrieve, or generate until restored. It preserves its full
  evidence and report history. Permanent deletion is an independent,
  explicitly confirmed operation.
- **2026-07-11 — claim identity:** A Claim has a stable identity from first
  generation or user creation and keeps it through ordinary text edits and
  Report Revisions. Deletion retires it. Splitting or merging Claims creates
  new identities; the system does not infer a provenance-preserving identity
  from text similarity.
- **2026-07-11 — citation identity and refresh:** A logical Claim Citation
  has a stable identity, while every evidence set is an immutable Citation
  Revision. Successful refresh creates a successor revision and supersedes the
  prior one without overwriting it, preserving the exact sources and anchors
  used by earlier report revisions.
- **2026-07-12 — evidence readiness:** Selection and readiness are separate.
  A Selected Paper may be awaiting an authorised file, importing, parsing,
  indexing, ready, failed, or unavailable; only its active ready Document
  Version can enter new retrieval, generation, or Claim Citations. Failures
  retain their phase and retry action. A ready predecessor remains usable
  while a successor is processed, as decided for version replacement.
- **2026-07-12 — outline/report relation:** Changing the current Report
  Outline does not invalidate the Claims or Claim Citations in an existing
  Literature Report. The report retains the Outline Revision it used and is
  marked out of sync with the current outline. Regeneration uses the current
  approved outline to create a new Report Revision; prior reports remain
  editable, exportable, and traceable.
- **2026-07-12 — version-replacement state (superseded detail):** The later
  report-lifecycle decision refines the prior pending-review treatment: when a
  cited Document Version leaves the active evidence boundary, the current Claim
  Citation is `evidence_unavailable` until the user refreshes it. Historical
  SourceAnchor snapshots remain inspectable.

## Resolution

The Research Workspace is the sole evidence boundary. It is created in
`setup`, becomes `active` when used, and can be `archived` (read-only) and
restored; permanent deletion is explicit. Every persisted Workspace,
Candidate Paper, Selected Paper, Document Version, outline/report revision,
Claim, Claim Citation, Citation Revision, and Source Chunk has an immutable,
opaque internal ID. All evidence relationships must carry the same workspace
ID. External provider IDs, DOI/arXiv IDs, URLs, and hashes provide provenance
and deduplication only.

A Candidate Paper becomes a Selected Paper only by explicit selection (or
direct upload registration). Selection may be removed without destroying
history, but it ends that paper's active-evidence eligibility. A selected paper
is usable only if its active Document Version is `ready`; version processing
otherwise reports `awaiting_authorised_file`, `importing`, `parsing`,
`indexing`, `failed`, or `unavailable`, with failure phase and retry action.
Replacement and reprocessing create a new immutable Document Version. The
predecessor stays active until the successor is ready, then the switch is
atomic; failed processing leaves the predecessor intact.

Outlines and reports form immutable saved revisions at save, generation, or
approval. A report records the Outline Revision it used; a changed current
outline merely makes that report out of sync. A Claim has a stable identity
across ordinary edits and report revisions; deletion retires it, while split or
merge creates new Claim identities. A logical Claim Citation has stable
identity and one or more immutable Citation Revisions, each retaining the
Source Chunk IDs and SourceAnchor snapshots used at that time. Refresh creates
a successor revision instead of overwriting evidence.

Citation review states are `verified`, `pending_review`, `user_confirmed`,
`removed`, and `evidence_unavailable`. Presentation-only edits preserve the
state. Any content change moves the Citation to `pending_review`; the system
does not claim the changed text remains supported. The user may confirm after
inspecting evidence, remove it, or refresh it. Only a refresh that validates
sources retrieved from the active workspace's ready Selected Papers can restore
`verified`. Removing evidence, replacing its active document version, or
otherwise leaving the active evidence boundary makes it
`evidence_unavailable` and prevents it from being `verified`; historical report
and citation snapshots remain inspectable.

### Invariants

- Candidate Papers are never parsed, indexed, retrieved, generated from, or
  cited before explicit selection and active evidence readiness.
- Every new retrieval, generation, refresh, and Citation Revision must
  reference the same Research Workspace and an active, ready Selected Paper's
  current Document Version. Historical Citation Revisions may retain their
  original Document Version and SourceAnchor snapshots.
- A Claim Citation keeps its resolved SourceAnchor snapshot; neither
  reprocessing nor a current index may rewrite a historical anchor.
- Only sources present in the operation's workspace-scoped retrieved-source
  registry may be retained by generation or refresh.
- Reports from an earlier revision remain inspectable and exportable, but only
  the current report revision participates in new retrieval and citation
  refresh.
