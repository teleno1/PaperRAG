# PaperRAG

PaperRAG is a trustworthy research-paper reading and reporting workspace for
individual researchers and graduate students. Users provide a research topic,
add papers, and receive a report whose claims can be traced back to the cited
paper content.

## Product Language

**Corpus**:
The bounded collection of source documents that the system is allowed to ingest,
index, and retrieve from for a given workflow or evaluation run.
_Avoid_: Dataset, knowledge base dump

**Document**:
A source file or frozen source snapshot that is treated as one ingestible unit
before chunking. A Research Paper is a specialised Document.
_Avoid_: treating every Document as a Research Paper

**Document Version**:
An immutable imported or uploaded artifact of a Document, including the parsed
and chunked evidence derived from it. Reprocessing or replacing a paper creates
a new Document Version; it does not rewrite the provenance of a prior version.
Existing Claim Citations to the predecessor remain inspectable as historical
evidence but become evidence-unavailable for the current report; they require
an explicit refresh rather than automatic remapping to the replacement.
_Avoid_: resolving a historical Claim Citation against whichever copy of a
paper is currently indexed

**Research Paper**:
An academic paper supplied by the user or discovered for a research topic. It
is the primary source type in the first product version.
_Avoid_: generic Document when the scholarly role matters

**Research Workspace**:
The bounded working set for one reporting task: its topic, selected Research
Papers, ingestion/index state, generated reports, and provenance records.
_Avoid_: Corpus when describing the user-facing unit of work

**Workspace State**:
The lifecycle status of a Research Workspace: setup while it is being formed,
active while it can process or use its evidence, and archived when its history
is read-only. An archived workspace can be restored; permanent deletion is a
separate, explicit action.
_Avoid_: treating removal of a paper as deletion of its workspace history

**Workspace Operation**:
A durable background operation within one Research Workspace, such as import,
parsing, indexing, outline/report generation, or citation refresh. It has an
opaque ID, persisted progress and phase, and one of `queued`, `running`,
`succeeded`, `failed`, `interrupted`, or `cancelled` states. Only a queued
operation may be cancelled; a running operation is allowed to finish or fail
rather than being forcefully interrupted. A service restart changes an
unfinished operation to `interrupted`; the user may retry it, and it must never
be represented as completed.
State-changing operations within the same Research Workspace execute serially;
the deployment applies a small global concurrency limit across workspaces. A
batch import may use controlled internal parallelism while remaining one
Workspace Operation. Its user-visible history records phase timestamps,
completed and total work, the current paper or section when applicable, and a
safe error category with a retry action; it never exposes secrets, raw prompts,
or complete paper content.
_Avoid_: making a browser request wait for a long operation or losing its state
on a server restart

**Persistent Identifier**:
An immutable, opaque internal identifier assigned to each persisted workspace,
paper record, document version, report revision, Claim, Claim Citation,
Citation Revision, and Source Chunk. Provider identifiers, URLs, and hashes
are provenance and deduplication attributes, not authority to cross a
Research Workspace boundary.
_Avoid_: using DOI, provider IDs, paths, or content hashes as a workspace-wide
identity or cross-workspace evidence reference

**Workspace Owner**:
The sole user of a first-version deployment. Research Workspaces are private to
that deployment; account registration, collaboration, and shared workspaces
are outside the first-version boundary.
_Avoid_: implying multi-user access control exists in the first version

**Candidate Paper**:
A Research Paper returned by topic search that has not yet been selected by the
user. Candidate Papers are not parsed, indexed, or cited as evidence.
_Avoid_: Source before the user selects it

**Selected Paper**:
A Candidate Paper the user has explicitly included in a Research Workspace, or
a paper the user uploaded directly. Only Selected Papers are eligible for
parsing, indexing, retrieval, and citation. Removing it ends that eligibility
in the current workspace while preserving its historical provenance; Claim
Citations that depend on it cannot remain verified. It becomes usable evidence
only when its active Document Version is ready.
_Avoid_: treating all search results as evidence

**Evidence Readiness**:
The processing status of a Selected Paper's active Document Version:
awaiting-authorised-file, importing, parsing, indexing, ready, failed, or
unavailable. Only ready evidence may be used for new retrieval, generation, or
Claim Citations; failures retain a phase and retry action.
_Avoid_: treating paper selection or a partially processed file as evidence

**Evidence Coverage**:
The explicit set of ready Selected Papers used for one report-generation or
citation-refresh operation, together with the selected papers excluded because
they were not ready and the reason for each exclusion. When the selected set is
mixed, the user must deliberately choose to generate from the ready subset;
later readiness does not silently alter an existing report.
_Avoid_: presenting a report based on a partial ready subset as if every
Selected Paper had contributed

**Paper Discovery**:
Topic-based retrieval of Candidate Paper metadata and links from open academic
indexes. The first product version automatically imports only publicly
downloadable PDFs; a restricted paper remains metadata and an external link
until the user supplies an authorised file.
_Avoid_: scraping or importing paywalled full text

**Literature Report**:
An editable, topic-oriented report generated from a Research Workspace. Each
supported claim can link to one or more cited source chunks. A saved report
revision is immutable; the current draft may become a new revision.
Generation may produce supported parts while marking a requested part with an
explicit evidence-gap note when the selected ready papers contain insufficient
support; it must not invent an uncited factual conclusion. No Literature Report
body can be generated when the workspace has no ready evidence.
_Avoid_: Answer when the intended output is a multi-source research artifact

**Report Language**:
The single language selected by the user for a Research Workspace's Literature
Report. The first version defaults to Chinese and supports Chinese or English;
it does not create parallel translations.
_Avoid_: inferring a report language solely from the papers' language

**Report Outline**:
The editable plan for a Literature Report, produced after paper selection and
approved or modified by the user before body generation. The first-version
default covers the research question, methods and findings, comparison,
limitations or research gaps, conclusion, and references. Changing the current
outline does not invalidate a report generated from an earlier Outline Revision;
that report remains traceable but is out of sync with the current outline.
_Avoid_: treating a one-shot long-form generation as the reporting workflow

**Outline Status**:
The current approval state of a Report Outline: draft while it is being created
or edited, and approved only after the user explicitly approves that exact
Outline Revision. A Literature Report may be generated only from an approved
outline; editing an approved outline returns the new current revision to draft
and leaves earlier reports traceable but out of sync.
_Avoid_: implicitly treating an edited outline as approved

**Report Revision**:
An immutable saved version of a Report Outline or Literature Report. Prior
revisions retain their claim and provenance history, but only the current
revision may be used for new retrieval or citation refresh; any saved report
revision may still be inspected, exported, or used as the basis for a new
revision. Regeneration creates a separate new report draft; it becomes current
only when the user explicitly selects it, so it never overwrites the prior
current report.
_Avoid_: treating browser edits or a regenerated report as if they overwrite
the provenance of earlier report content

**Report Draft**:
The current editable, automatically persisted working copy of a Literature
Report. Browser refresh must retain it, but it becomes an immutable Report
Revision only when the user explicitly saves a version. Generation,
regeneration, and export operate from persisted report content, never from an
unsaved browser-only state.
_Avoid_: losing ordinary editing work or treating every keystroke as a version

**Report Operation Attempt**:
A recorded attempt to generate an outline, generate or regenerate a Literature
Report, or refresh a Claim Citation. It captures the relevant persisted input
snapshot, including the Outline Revision and Evidence Coverage where relevant.
A failed attempt reports its phase and permits retry with the same inputs, but
does not overwrite current content or evidence; incomplete streamed output is
not a Report Draft or a Claim Citation.
_Avoid_: treating a failed or partially streamed operation as saved report
content

**Report Trust Summary**:
The report-level user-visible summary of its Evidence Coverage, the count of
each Citation Review State, and any evidence-gap notes. A report with evidence
gaps, pending-review citations, or evidence-unavailable citations is marked as
needing attention; otherwise it is ready to export. This product-facing
summary does not use the legacy offline-evaluation labels.
_Avoid_: presenting a partial or unresolved report as unqualifiedly complete

**Claim Citation**:
A user-visible, one-to-many provenance link from a supported sentence or report
bullet to the Source Chunks that support it. Selecting it reveals the paper
title, page or section location, and source excerpt in a side panel. Its
evidence is retained as immutable Citation Revisions rather than overwritten
when refreshed. A refresh searches only ready, active Selected Papers in the
same Research Workspace and records its resulting Evidence Coverage; it may
therefore use newly selected or newly ready papers, but never another
workspace's evidence.
_Avoid_: one citation for an entire report paragraph by default

**Citation Revision**:
An immutable evidence snapshot for a Claim Citation, including its Source
Chunks and SourceAnchors. A successful refresh creates a successor revision;
the previous revision remains traceable as superseded. A refresh that finds no
valid support creates no successor and leaves the current Claim Citation pending
review with an explicit no-support result.
_Avoid_: replacing historical evidence in place

**Claim**:
A stable logical report sentence or bullet that may have Claim Citations. Its
identity survives ordinary edits across Report Revisions, but is retired when
deleted; splitting or merging Claims creates new identities rather than
inferring provenance by text similarity.
_Avoid_: treating every rendered string or a split/merged claim as the same
claim without an explicit identity decision

**Citation Review State**:
The trust status of a Claim Citation. A generated citation is verified against
its retrieved evidence. A presentation-only edit preserves that state; a
substantive claim edit makes it pending review. A substantive edit is any
change to the Claim's visible text after whitespace normalization; formatting,
layout, and citation-marker-only changes are presentation-only. A user may
confirm it after reviewing the evidence, which makes it user-confirmed rather
than verified, remove it, or refresh it; only successful refresh can restore
verified. If any Source Chunk in a current Citation Revision leaves the active
workspace boundary, the entire Claim Citation is evidence-unavailable and
cannot be verified, even when it also contains other still-active chunks.
_Avoid_: showing an unchanged citation as verified after its claim changes

**Chunk**:
A contiguous unit of document content produced by parsing and chunking, used as
the primary retrieval payload.
_Avoid_: Passage, snippet

**Source**:
A traceable retrieval reference exposed to users and evaluators, usually tied to
one chunk and identified by `source_id`.
_Avoid_: Citation entry, reference row

## Legacy Generic-Evaluation Vocabulary

The terms below describe retained evaluation code and fixtures from the
superseded generic-RAG refactor. They are not the active product's definition
of success; see `docs/wayfinder/research-paper-workspace.md` for current
product planning.

**Answer Expectation**:
The offline evaluation label that states whether a case should be fully
answered, partially answered, or refused based on available corpus evidence.
_Avoid_: Mode, answer type

**Full Answer**:
An evaluation case where the corpus contains enough evidence to support the
requested answer directly.
_Avoid_: Normal case, positive case

**Partial Answer**:
An evaluation case where the corpus supports only part of the requested answer,
and the unsupported remainder must be explicitly left unresolved.
_Avoid_: Soft negative, incomplete positive

**Abstain**:
An evaluation case where the corpus does not support the requested answer, so a
grounded refusal or explicit statement of missing evidence is the correct behavior.
_Avoid_: No answer, hard negative

**Expected Source**:
A `source_id`-level gold evidence reference used only for offline evaluation to
judge retrieval and grounding quality.
_Avoid_: Gold chunk, runtime hint

**Unsupported Aspect**:
A requested detail that the corpus does not support and that the system must not
hallucinate as grounded.
_Avoid_: Missing field, negative note
