# 05A — Index Ready Selected Paper Evidence

**What to build:** A researcher can prepare each Selected Paper as real,
workspace-scoped vector evidence: after parsing, the active Document Version is
chunked with traceable locations, embedded with `text-embedding-v4`, and added
to the workspace FAISS index before it is presented as ready for a Literature
Report.

**Blocked by:** None — can start immediately. Tickets 01 and 02 already
establish Selected Papers and their processing lifecycle.

**Status:** ready-for-agent

**Supersedes as a delivery prerequisite:** The indexed-evidence portion of the
historical 05 report shell. Historical 05 remains complete; it is not a real
vector-RAG completion claim.

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

- [ ] A Selected Paper becomes Evidence Ready only after its active Document
  Version is chunked without crossing parsed section boundaries, with roughly
  500-token/two-sentence-overlap policy, Chinese/English sentence boundaries,
  and versioned paper/section/page/character SourceAnchor metadata.
- [ ] Chunks and query embeddings use Alibaba Cloud `text-embedding-v4` and a
  Research Workspace-isolated FAISS index; removal or replacement of a paper
  cannot make its old chunks eligible for new retrieval.
- [ ] The browser and API truthfully expose indexing progress, safe provider or
  configuration failures, and retry; neither lexical search nor synthetic
  vectors may silently make a paper ready in production.
- [ ] Controlled collaborators cover persistence, metadata isolation, failure,
  and retry. A documented manual acceptance run uses the configured real
  embedding provider without committing keys, papers, indexes, or artifacts.

