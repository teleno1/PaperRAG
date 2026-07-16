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

**Paper Reading View**:
The desktop reading surface for a Selected Paper's active, authorised original
PDF. It displays the source PDF itself rather than reconstructed Chunk text,
summaries, or a chunk-assembled substitute. A Claim Citation can open this
view at its SourceAnchor's page, with a location cue when available. Annotation,
personal notes, and PDF editing are outside the first version.
If the original PDF is unavailable for a historical Citation Revision, the view
truthfully reports that condition and retains only its historical paper
metadata, location, and cited excerpt with recovery or refresh actions; it
never substitutes a reconstructed reader.
_Avoid_: chunk reader, reconstructed paper viewer

**Workflow Stage**:
One primary, user-selectable stage in the desktop Research Workspace journey.
The accepted desktop Workspace Interaction Architecture places four stages in
left-side navigation: literature import, paper reading, Report Outline
generation and editing, and report writing. Retrieval is controlled through
the editable section queries in the Report Outline; it has no separate
user-facing evidence-curation stage.
Selecting a stage changes the central task surface and its right-side
contextual detail surface; it is not the historical fixed three-panel layout or
a requirement to use drawer components.
All stages remain visible and selectable. When a prerequisite is absent, the
central surface explains it and offers the next permitted action rather than
hiding the stage or leaving an unexplained disabled control.
_Avoid_: a permanently visible generic panel

**Task Detail Pane**:
The right-side contextual surface paired with the active Workflow Stage. It
shows the stage-specific supporting information and actions--for example import
progress and ready papers, available papers while reading, saved outline
versions, operation status, ready papers, or Claim evidence and trust details.
It does not define the product's information architecture independently of the
active stage.
_Avoid_: a universal drawer

**Focused Claim**:
The Claim selected from the Literature Report for citation inspection. Hovering
over a cited Claim gives its sentence area a light-grey, bottom-emphasised
background affordance; selecting it retains a clear highlight and opens its
Claim Citations in the Task Detail Pane. The user can then open a
chosen source in the Paper Reading View.
_Avoid_: a citation marker as the only interactive target

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
Indexing includes creating embeddings for that version's Chunks and adding them
to a Research Workspace-isolated vector index with the paper, document-version,
Chunk, and SourceAnchor metadata needed for retrieval and provenance. A
chapter-generation retrieval searches only the current, ready Selected Papers
in that workspace.
_Avoid_: treating paper selection or a partially processed file as evidence

**Evidence Coverage**:
The explicit set of ready Selected Papers used for one report-generation or
citation-refresh operation, together with the selected papers excluded because
they were not ready and the reason for each exclusion. When the selected set is
mixed, only ready papers may supply body evidence; later readiness does not
silently alter an existing report.
For body generation, Evidence Coverage is established when a Report Operation
Attempt freezes the automatic retrieval results for the approved Outline
Revision. It contains the ready papers represented by that attempt's Chapter
Evidence Bundles. The Workspace Owner edits and versions the outline's section
queries, but does not manually curate individual Chunks in a separate stage.
_Avoid_: presenting a report based on a partial ready subset as if every
Selected Paper had contributed

**Planning Evidence Bundle**:
The bounded evidence input used only to propose a Report Outline. It is built
from three to five queries derived from the topic and research question,
vector-retrieved from the ready Selected Papers in the Research Workspace, and
re-ranked with paper-level deduplication and maximal marginal relevance. It
contains roughly twelve to twenty representative Chunks, with no paper
contributing more than two, and retains each Chunk's title, concise excerpt,
and SourceAnchor. It guides outline structure but never becomes a body Claim
Citation.
_Avoid_: treating planning retrieval as report-body evidence

**Chapter Evidence Bundle**:
The immutable, automatic retrieval result used for one body chapter in a
Report Operation Attempt. It records the approved Outline Revision's section
queries, eligible ready Selected Papers, retrieved Source Chunks, scores,
query attribution, and any evidence-gap result. It establishes the attempt's
Evidence Coverage and is frozen with that attempt; later paper readiness or
outline edits never rewrite it. The Workspace Owner controls retrieval by
editing and versioning the Report Outline's section queries, not by manually
adding or removing individual Chunks.
_Avoid_: Evidence Curation Version, an unrecorded retrieval override

**Paper Discovery**:
Topic-based retrieval of Candidate Paper metadata and links from open academic
indexes. The first product version automatically imports only publicly
downloadable PDFs; a restricted paper remains metadata and an external link
until the user supplies an authorised file.
_Avoid_: scraping or importing paywalled full text

**Demonstration Corpus**:
A fixed set of ten open-access Research Papers used to demonstrate and manually
accept the product workflow: three RAG foundation/retrieval-method papers,
three evidence-attribution or citation-mechanism papers, two evaluation or
factual-consistency papers, and two limitation, comparison, or failure-mode
papers. Its first topic is RAG evidence attribution and citation reliability;
the source papers may be English while the demonstration Literature Report is
Chinese. The repository retains only a manifest of stable identifiers,
versioned public-PDF locations, checksums, and licence/provenance information,
never the papers or their derived artifacts. A separate controlled acceptance
fixture, rather than a deliberately broken public URL, creates unready or
failed paper states for repeatable recovery demonstrations.
A real demonstration preflight must validate all ten papers and fails rather
than silently substituting a smaller set; CI uses only offline controlled
collaborators. Demonstration preparation always uses an explicitly selected,
empty, isolated data directory and must never clear a user's normal workspace.
_Avoid_: treating the legacy generic-evaluation corpus as product evidence

**Literature Report**:
An editable, topic-oriented report generated from a Research Workspace. Each
supported claim can link to one or more cited source chunks. A saved report
revision is immutable; the current draft may become a new revision.
Generation may produce supported parts while marking a requested part with an
explicit evidence-gap note when the selected ready papers contain insufficient
support; it must not invent an uncited factual conclusion. No Literature Report
body can be generated when the workspace has no ready evidence.
For each approved outline section, generation returns structured Claims, each
with one or more Source Chunk IDs drawn only from that section's retrieval
result, or an explicit evidence-gap result. The service validates those IDs
before creating Claim Citations and rejects or retries a factual Claim that has
no valid cited evidence.
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
Outline generation is a real model operation: a planning retrieval first
builds a Planning Evidence Bundle across the ready Selected Papers, then the
model receives that evidence with the topic and research question to propose
the editable outline. Planning evidence informs structure only; it is not a
Claim Citation for the generated report body.
The model returns schema-validated JSON with ordered chapters and their ordered
sections. Each chapter declares a role: body, conclusion-and-outlook, abstract,
or references. A body chapter has a title and sections; every such section has
a title, an objective, expected_claims, and one or more retrieval queries.
Conclusion-and-outlook may specify additional outlook queries; abstract and
references specify none. The service, rather than the model, assigns persistent
identifiers, revision/status data, order, and the model and planning-evidence
snapshots. Ordinary title or ordering edits retain section identity; deletion,
splitting, or merging creates a new one.
The schema requires exactly one abstract first, one or more body chapters, one
conclusion-and-outlook after all body chapters, and exactly one references
chapter last. A response with a different role set or order is invalid and uses
the ordinary one-repair JSON rule.
Its prompt has four fixed parts: system rules limiting it to evidence-based
planning and JSON-only output; the topic, research question, language and
scope; the bounded Planning Evidence Bundle; and the JSON Schema/output rules.
The first generation receives no old outline. Regeneration additionally
receives the current outline and an explicit user instruction, then returns a
complete replacement outline.
Each body section supplies one or more retrieval queries. Their results form
the evidence available to its body chapter; the body chapter, not the section,
is the smallest generation and scheduling unit. A body chapter generates and
validates its Claims from its bounded evidence before the chapters are composed
into a Literature Report. It can therefore be retried without silently reusing
another chapter's evidence.
Each section query vector-retrieves eight candidates. The chapter deduplicates
their union and applies maximal marginal relevance, retaining twelve to eighteen
Chunks with no paper contributing more than three. Every retained Chunk records
the section and query that retrieved it, as well as its provenance metadata.
The first version records normalized similarity scores but applies no fixed
score cutoff as a proxy for support: it always uses the bounded top candidates,
then relies on Claim support validation to decide whether evidence is adequate.
Any cutoff must be calibrated later from real ten-paper demonstration outcomes,
not guessed during initial implementation.
When every query for a body section has no candidate, the service creates that
section's evidence-gap block without calling the body model. If that applies to
every section of a body chapter, the chapter completes as an all-gap result;
otherwise the model receives only sections with evidence and the existing gaps.
The body-generation prompt has fixed system rules, report/chapter/section
context, the chapter Evidence Bundle, and a JSON output contract. It returns
each section as ordered blocks. A factual block is one independently editable
sentence or bullet Claim with its proposed Source Chunk IDs; an unsupported
part is an evidence-gap block with a reason. It may not fill a gap with an
uncited factual statement. Rendering those blocks into Markdown or paragraphs
does not change their Claim identities or citations.
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
The accepted Desktop Workspace Experience presents it as continuous report
text, not separate preview and editing modes. A cited sentence remains an
interactive Claim target; chapter-level regeneration accepts a written
instruction beside that chapter. Any direct editing surface still preserves the
automatic persistence and explicit-version rules above, but it must not invent
a mode toggle or a permanent writing assistant that the Interaction Contract
did not accept.
_Avoid_: losing ordinary editing work or treating every keystroke as a version

**Report Operation Attempt**:
A recorded attempt to generate an outline, generate or regenerate a Literature
Report, or refresh a Claim Citation. It captures the relevant persisted input
snapshot, including the Outline Revision and Evidence Coverage where relevant.
A failed attempt reports its phase and permits retry with the same inputs, but
does not overwrite current content or evidence; incomplete streamed output is
not a Report Draft or a Claim Citation.
An attempt freezes the approved outline, Evidence Coverage, model configuration,
and each chapter's Evidence Bundle. If a chapter fails, completed chapter
results remain available inside that attempt but no new draft is published. A
retry reruns only failed chapters and then their dependent chapters and final
integration; a user-requested regeneration creates a new attempt rather than
reusing prior generated content.
It persists a ChapterRun for each chapter (role, phase, state, retry count,
timestamps, and safe error category), its ChapterEvidenceBundle (section
queries, candidate/final Chunk IDs, scores, MMR order, and query attribution),
and ClaimCandidates (blocks, proposed Chunk IDs, validation verdict/reason, and
regeneration count). These are normalized IDs and JSON snapshots, never raw
prompts, complete paper content, or credentials; the browser exposes only safe
progress and errors.
Report generation records its chapter progress, but it publishes a new editable
Report Draft only once every body chapter has reached either a validated
cited-Claim result or an explicit evidence-gap result and all dependent
chapters have completed. A retrieval or model failure publishes no partial
draft and leaves the prior draft unchanged.
Eligible body chapters process in bounded parallelism with a deployment-
configurable default of two chapter workers. Within a chapter, query retrieval,
generation, support checking, and any one regeneration run serially. The
conclusion-and-outlook chapter waits for the body chapters and may retrieve
evidence only for its outlook portion; the abstract waits for the completed
report and uses no retrieval or new citations. References always exist and are
rendered deterministically from the attempt's Evidence Coverage, with no
retrieval or model call. Every ready paper in that coverage appears, marked
either cited when a verified Claim Citation uses it or consulted-but-uncited
otherwise. Only cited papers have clickable body citations. The final synthesis
model does not rewrite, reorder,
or otherwise polish verified body Claims; any factual change returns that Claim
to its chapter's retrieval, generation, and validation flow.
The final synthesis model receives immutable verified body Claim blocks, their
citation bindings, and evidence gaps. Its conclusion derives only from existing Claim IDs
and inherits their citations; its outlook uses separately retrieved and
validated Claims. Its uncited abstract may only compress existing verified
Claims and may not add facts. References never enter its output.
It returns schema-validated JSON: conclusion and abstract entries contain text
and one or more derived_from_claim_ids; outlook entries are cited Claims or
evidence gaps. The service expands a conclusion's inherited Source Chunks and
checks support again. Abstract derivation is retained internally to prevent new
facts, but its citations are never rendered or exported.
Verified body citations use `[n]` in first-appearance order. The references
chapter uses the same numbering, then appends consulted-but-uncited papers with
their status. Chinese reports use GB/T 7714 field ordering and English reports
the corresponding numbered English rendering; missing bibliographic metadata
is omitted rather than invented.
Production outline, embedding, and report-generation operations use configured
external model providers: Alibaba Cloud `text-embedding-v4` for embeddings and
`deepseek-v4-flash` for outline, generation, support checking, and integration.
Their keys are read only from the local `DASHSCOPE_API_KEY` and
`DEEPSEEK_API_KEY` environment variables; model configuration snapshots retain
provider, model, parameters, and prompt version but never a key. Missing
configuration, provider failure, or invalid model output fails the operation
with a safe retryable error; it must not silently substitute a template,
lexical retrieval, or fabricated content.
Deterministic model collaborators are test-only, and real-provider manual
acceptance is required before a model-backed delivery ticket is complete.
Every JSON-producing model phase validates its output against the applicable
schema. On its first parse or validation failure, the service supplies the
validation error to that role and requests one repair; a second failure fails
the phase and preserves the Report Operation Attempt for retry. The service
never guesses a JSON structure through permissive extraction or substitutes a
template.
The deployment defaults are temperature 0.3 for outline planning, 0.2 for body
generation, 0 for support validation, and 0.2 for final integration. Each role
has its own output-token limit. Parameters and prompt-template versions are
snapshotted in the attempt; first-version users do not tune them in the browser.
_Avoid_: treating a failed or partially streamed operation as saved report
content

**Report Trust Summary**:
The report-level user-visible summary of its Evidence Coverage, the count of
each Citation Review State, and any evidence-gap notes. A report with evidence
gaps, pending-review citations, or evidence-unavailable citations is marked as
needing attention; otherwise it is ready to export. This product-facing
summary does not use the legacy offline-evaluation labels.
_Avoid_: presenting a partial or unresolved report as unqualifiedly complete

**AI Rewrite Proposal**:
A user-requested, non-destructive proposed revision to a selected Claim or
explicitly selected report passage. Before it can replace report text, the
service checks each changed factual Claim against its current Source Chunks.
The user may apply a supported proposal as verified content; a partially
supported or unsupported proposal is shown with its validation reason but never
automatically replaces the draft, and the user may reject it, retain it as
pending review, or refresh its citations. Original Claim text and Citation
history remain inspectable in every outcome.
_Avoid_: silent AI overwrite, unverified rewrite

**Claim Citation**:
A user-visible, one-to-many provenance link from a supported sentence or report
bullet to the Source Chunks that support it. Selecting it reveals the paper
title, page or section location, and source excerpt in the Task Detail Pane. Its
evidence is retained as immutable Citation Revisions rather than overwritten
when refreshed. A refresh searches only ready, active Selected Papers in the
same Research Workspace and records its resulting Evidence Coverage; it may
therefore use newly selected or newly ready papers, but never another
workspace's evidence.
Before a generated Claim Citation is marked verified, a separate support check
receives only the Claim and its proposed Source Chunks and classifies the
support as supported, partially supported, or unsupported. An unsupported
Claim is regenerated once; if it still lacks support, the report records an
explicit evidence gap rather than a verified citation.
The support check is batched per body chapter for efficiency, while each input
item remains limited to one Claim and its proposed Chunks. It returns the Claim
identifier, verdict, and reason. Both partially_supported and unsupported
Claims are regenerated once using that reason and then checked again; only
supported creates a verified Claim Citation.
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
substantive direct claim edit makes it pending review. An applied AI Rewrite
Proposal may remain verified only after its changed factual Claims pass the
same support check against their current Source Chunks; otherwise it follows the
ordinary pending-review path. A substantive edit is any change to the Claim's
visible text after whitespace normalization; formatting, layout, and
citation-marker-only changes are presentation-only. A user may confirm it after
reviewing the evidence, which makes it user-confirmed rather than verified,
remove it, or refresh it; only successful refresh can restore verified. If any
Source Chunk in a current Citation Revision leaves the active workspace
boundary, the entire Claim Citation is evidence-unavailable and cannot be
verified, even when it also contains other still-active chunks.
_Avoid_: showing an unchanged citation as verified after its claim changes

**Chunk**:
A contiguous unit of document content produced by parsing and chunking, used as
the primary retrieval payload. It never crosses a parsed title/section boundary,
is limited to roughly 500 tokens with a two-complete-sentence overlap, and
recognises both Chinese and English sentence boundaries. It retains the
Research Paper, Document Version, section title, page start/end, character
start/end, and clean excerpt needed to form a SourceAnchor. Tables and formulas
are not independently embedded in the first version, though their parsed
adjacent explanatory text may be part of a Chunk.
_Avoid_: Passage, snippet

**Source**:
A traceable retrieval reference exposed to users and evaluators, usually tied to
one chunk and identified by `source_id`.
_Avoid_: Citation entry, reference row

**Interaction Prototype**:
A disposable, controlled-fixture representation of the complete Research
Workspace journey used to accept its information architecture, controls, and
recovery interactions before production browser implementation. Its ordinary
path is operated step by step from workspace setup through export. Its
prototype-only scenario switcher reaches failure, partial-readiness,
evidence-gap, multi-source, and citation-review states efficiently; every such
state remains operable rather than a static screen. It may simulate providers
and persistence, but it never establishes production evidence or substitutes
for real-provider product acceptance.
It runs independently from the production browser application and production
APIs; only its accepted interaction decisions, state model, and control
inventory are implementation inputs.
It is a high-fidelity desktop experience: realistic information density,
hierarchy, typography, controls, feedback, and disabled states are required to
assess usability, though providers, files, and persistence may be controlled
fixtures.
_Avoid_: mock demo, static screen set

**Desktop Workspace Experience**:
The first-version interaction target for the Research Workspace and its
Interaction Prototype. It is designed and accepted for desktop browsers where
paper reading, long-form report editing, and evidence comparison can coexist.
Mobile and narrow-screen responsive layouts are outside the current product and
prototype scope; they must not silently consume delivery capacity or become an
acceptance requirement.
_Avoid_: responsive-first workspace

**Workspace Interaction Architecture**:
The accepted desktop information architecture through which the Workspace Owner
prepares papers, plans, generates, edits, traces, reviews, and exports a
Literature Report. It must make every permitted action and recovery path
discoverable at the state where it is needed while preserving the evidence
boundaries defined elsewhere in this glossary. The former fixed three-panel
layout is a retired historical candidate, not a product constraint. The
accepted architecture is an iterated flow-driven desktop workspace with four
left-navigation stages: literature import, paper reading, Report Outline, and
report writing. Its central task surface and right Task Detail Pane scroll
independently. Retrieval is controlled by versioned outline queries rather
than a fifth evidence-curation stage; report writing uses continuous text and
chapter-level regeneration rather than a preview/edit mode split. The completed
prototype compared three candidates and then covered exceptional and recovery
states.
_Avoid_: treating a panel arrangement as a domain rule

**Interaction Contract**:
The accepted, prototype-derived inventory that maps every visible Workspace
state to its available controls, their location and enablement conditions,
their resulting and recovery states, editing/confirmation rules, and the
corresponding domain objects. It is the browser-acceptance source for delivery
work after an Interaction Prototype is accepted, preventing an implementation
from silently omitting a necessary action or state.
_Avoid_: an informal list of screens or a visual-only mockup

**Interaction Architecture Candidate**:
One materially distinct, operable desktop arrangement of the Research Workspace
that obeys the same domain rules and complete normal journey as other
candidates. The first comparison contains a flow-driven workspace, a
report-driven writing desk, and an evidence-driven research desk; visual
restyling of one arrangement is not a separate candidate. All first-round
candidates share one high-fidelity, restrained research-writing visual baseline
so their information architecture and interaction organisation, rather than
themes or component skins, are compared.
_Avoid_: theme variant

**Accepted Interaction Architecture**:
The one desktop interaction architecture that the Workspace Owner explicitly
accepts after comparing Interaction Architecture Candidates and iterating on a
selected or hybrid direction. Candidates are diagnostic starting points, not a
closed menu: the owner may combine their successful elements and request
further changes until satisfied. Delivery work begins only after this resulting
architecture and its Interaction Contract are accepted.
_Avoid_: treating an unmodified candidate as automatically final

**Prototype Acceptance Gate**:
The explicit Workspace Owner decision that an Accepted Interaction Architecture
and its Interaction Contract are sufficient to guide production browser work.
It follows two checkpoints: first, the owner completes the normal journey in
every Interaction Architecture Candidate and selects, combines, or redirects a
direction; second, the owner completes the Prototype Journey Boundary and all
its recovery states in the resulting single architecture and accepts its
contract. The gate may involve any number of iterations, each with recorded
changes and an updated contract. No unfinished vertical delivery ticket that
contains browser behaviour begins before this gate; completed delivery work is
not retroactively reopened solely by the gate.
_Avoid_: beginning a minimal UI while the interaction architecture is undecided

**Prototype Fixture**:
A deterministic, local research scenario used only by an Interaction Prototype.
It supplies realistic Chinese research-workspace content: a topic, ten paper
records with varied readiness, representative source excerpts, report content,
citations, and recovery states. It never reads a real PDF, makes a network
request, or calls a model, so repeated interaction review reaches the same
state without being mistaken for provider or ingestion acceptance evidence.
_Avoid_: live demo data, production fixture

**Prototype Operation State**:
The Interaction Prototype's faithful, operable representation of a Workspace
Operation lifecycle: queued, running, succeeded, failed, interrupted, or
cancelled. Only queued operations may be cancelled; failed and interrupted
operations expose retry. Report-generation fixtures also represent per-chapter
progress and a retry that retains completed chapter results. These controls
model the real lifecycle and must not imply a force-cancel capability that the
product does not have.
_Avoid_: decorative progress indicator

**Prototype Comparison Mode**:
An Interaction Prototype mode that places the same scenario behind every
Interaction Architecture Candidate and lets the Workspace Owner switch among
them while recording structured feedback. It prompts for task clarity,
next-action discoverability, information load, control discoverability, and
evidence-checking ease, alongside free notes and a link or screenshot for the
observed state. It informs iteration but never chooses an architecture on the
owner's behalf.
_Avoid_: visual preference poll

**Prototype Journey Boundary**:
The nine-part user journey that the accepted Interaction Prototype must make
operable: workspace setup; paper upload or discovery and selection; evidence
preparation and recovery; Report Outline generation, editing, query versioning,
regeneration, and approval; automatic retrieval and Evidence Coverage;
report generation and recovery; Report Draft editing and saving; Claim Citation
inspection; Citation Review; and Report Trust Summary followed by Markdown
export. Workspace archival and historical-version browsing are outside this
prototype boundary.
_Avoid_: treating background operations or citation recovery as secondary
screens

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
