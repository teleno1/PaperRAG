# 05A — Index Ready Selected Paper Evidence

**What to build:** A researcher can prepare each Selected Paper as real,
workspace-scoped vector evidence: after parsing, the active Document Version is
chunked with traceable locations, embedded with `text-embedding-v4`, and added
to the workspace FAISS index before it is presented as ready for a Literature
Report.

**Blocked by:** None — can start immediately. Tickets 01 and 02 already
establish Selected Papers and their processing lifecycle.

**Status:** complete

**Resolved:** 2026-07-14

**Historical UI note:** Superseded on 2026-07-15 by ADR 0006 and delivery
tickets 06 through 15. The deferred-layout constraint below describes the
historical indexing slice only; it is not a constraint on active work.

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

- [x] A Selected Paper becomes Evidence Ready only after its active Document
  Version is chunked without crossing parsed section boundaries, with roughly
  500-token/two-sentence-overlap policy, Chinese/English sentence boundaries,
  and versioned paper/section/page/character SourceAnchor metadata.
- [x] Chunks and query embeddings use Alibaba Cloud `text-embedding-v4` and a
  Research Workspace-isolated FAISS index; removal or replacement of a paper
  cannot make its old chunks eligible for new retrieval.
- [x] The browser and API truthfully expose indexing progress, safe provider or
  configuration failures, and retry; neither lexical search nor synthetic
  vectors may silently make a paper ready in production.
- [x] Controlled collaborators cover persistence, metadata isolation, failure,
  and retry. A documented manual acceptance run uses the configured real
  embedding provider without committing keys, papers, indexes, or artifacts.

## Delivered implementation

- `SourceAnchor` now survives parsed-unit chunking, chunk artifacts, FAISS
  metadata, workspace retrieval, and `SourceChunk` API responses. Chunk
  excerpts are clean source text; retrieval-only title/section decoration is
  kept out of the user-facing excerpt.
- Workspace indexing rebuilds only selected papers whose active Document
  Version is ready, writes under `workspace-files/<workspace-id>/index/`, and
  replaces the validated FAISS/metadata pair. A new version is indexed before
  its paper becomes ready; removing a selected paper rebuilds the eligible set.
- Production construction injects `DashScopeEmbeddingClient` and fails with a
  safe retryable indexing error when `DASHSCOPE_API_KEY`, the provider, or the
  returned vector batch is invalid. Directly injected test collaborators remain
  deterministic and do not provide a production fallback.
- Operation phase, completed/total work, safe error category, and retry action
  are persisted and exposed through the existing workspace API and browser
  operation card. The workspace report retriever uses the isolated vector
  index whenever the production embedding collaborator is present.

## Verification

Offline controlled-collaborator coverage is in
`tests/test_workspace_evidence_indexing.py` and covers cross-page anchors,
workspace metadata isolation, removal, persistence, provider failure, and
retry. The full verification commands are:

```powershell
pytest -q
cd frontend
npm.cmd run build
```

For manual provider acceptance, set `DASHSCOPE_API_KEY` only in the local
process environment, start the FastAPI app with the normal configured paths,
upload a small authorised PDF through the workspace UI, and confirm that the
operation reaches `indexing` and then `succeeded`, the paper reaches `ready`,
and a query/report retrieval returns the paper's `document_version_id`, page or
section anchor, and clean excerpt. Repeat once with the key unset and confirm
that the paper remains failed/retryable and no synthetic or lexical index is
published. Keep the PDF, index, metadata, and operation artifacts under the
ignored local data directory; do not add them to git.

Manual acceptance result (2026-07-14): the configured real
`text-embedding-v4` client completed a controlled workspace upload; the
operation reached `succeeded`, the paper reached `ready`, and the isolated
index contained the workspace and active Document Version metadata. The
temporary acceptance directory was outside the repository and was not
retained as a product artifact.
