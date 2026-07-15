# PaperRAG Architecture

This document describes the active target architecture for PaperRAG: a
single-user research-paper workspace that produces editable, claim-traceable
literature reports. The historical generic-RAG architecture and evaluation plan
are retained as [legacy material](legacy/README.md).

## Product Flow

```text
topic
  -> upload papers / discover Candidate Papers
  -> user selects papers for a Research Workspace
  -> durable Workspace Operations parse PDFs while retaining source locations
  -> chunks + embeddings + workspace index
  -> editable report outline
  -> cited Literature Report
  -> claim citation opens source paper excerpt(s)
  -> user edit marks affected citation pending review
  -> keep, remove, or refresh citation
```

## Current Foundation

The repository already contains a Python backend with these reusable pieces:

```text
PDF papers
  -> MinerU parsing
  -> normalized/chunk metadata
  -> DashScope embeddings
  -> FAISS index + metadata
  -> retrieval/rerank
  -> outline/review or report generation
  -> source and citation validation
```

`app/` remains layered as follows:

```text
api/              FastAPI routes and request/response translation
cli/              compatibility command-line surface
core/             config, paths, logging, and exceptions
domain/           pure product models and rules
infrastructure/   parsers, LLMs, vector store, exporters, external adapters
schemas/          API schemas
use_cases/        workflow orchestration
```

The existing PDF parser, chunker, FAISS persistence, retrieval service, LLM
clients, outline/report flow, and source validation are foundation—not the
finished workspace product.

The first workspace delivery slices now provide SQLite-backed Research
Workspace and Research Paper records, managed per-workspace paper files,
parser-backed readiness state, candidate discovery/import provenance, bounded
public-PDF verification, durable operation history, and versioned workspace API
routes for creating, revisiting, discovering, selecting, importing, and removing
papers. Ticket 03 adds the React + TypeScript preparation SPA, same-origin
compiled asset delivery, and the browser flow over this boundary. Ticket 04
adds workspace-scoped Report Outline revisions, ready-evidence gating, draft
editing, explicit approval, and immutable approved-history persistence. Cited
report generation and claim-level provenance now build on this boundary through
workspace-scoped Literature Report drafts, Claim Citations, Source Chunks, and
ready-evidence coverage snapshots. The report editor remains a small functional
surface until the later accepted workspace prototype.

05A completes the real evidence boundary: every processed version writes
provenance-aware `chunks.json`, and only ready Selected Papers contribute to a
workspace-specific `evidence.faiss` plus metadata pair. The validated pair is
replaced after Alibaba Cloud `text-embedding-v4` succeeds; provider or
configuration failure leaves the paper failed and retryable. Workspace
retrieval filters by the current selected paper and active Document Version,
so a removed or replaced version cannot become new evidence while an older
index is being rebuilt.

## Active Domain Model

The canonical terms are defined in [CONTEXT.md](../CONTEXT.md). Key concepts:

- `ResearchWorkspace`: one user-owned topic, selected papers, processing state,
  report versions, and provenance records.
- `CandidatePaper`: a discovery result that is not evidence until selected.
- `SelectedPaper`: an uploaded or user-approved paper eligible for parsing,
  indexing, retrieval, and citation.
- `Document` / `DocumentChunk`: the underlying ingestion and retrieval models;
  a Research Paper is a specialised Document.
- `LiteratureReport` and `ReportOutline`: user-editable, topic-oriented output.
- `ClaimCitation`: one report claim linked to one or more source chunks.
- `CitationReviewState`: verified, pending review, user-confirmed, removed, or
  evidence-unavailable. Substantive Claim edits invalidate verified status
  without deleting evidence history.
- `WorkspaceOperation`: durable import, parsing, indexing, generation, or
  refresh work with persisted progress and retryable terminal state.

## Architectural Boundaries

- **Domain** owns workspace, paper-selection, report, citation, and review-state
  rules; it has no FastAPI, filesystem, or HTTP dependency.
- **Use cases** orchestrate discovery, upload/import, parsing/indexing, outline
  approval, generation, citation refresh, and report export.
- **Infrastructure** implements MinerU-compatible parsing, source-location
  extraction, embeddings, FAISS, LLM calls, open-paper discovery adapters, and
  local persistence. SQLite accessed through `sqlite3` repository adapters is
  authoritative for workspace state, revisions, citations, and operations;
  managed local files hold PDFs, parsed artifacts, and workspace/version-scoped
  FAISS indexes. External services remain injectable for tests.
- **API** exposes versioned workspace-oriented JSON endpoints under
  `/api/workspaces/...` plus operation state at `/api/operations/{id}` and
  workspace operation history. It never exposes filesystem paths, vector-store
  internals, or provider details. Existing generic routes remain compatibility
  endpoints until product tickets replace or adapt them.
- **Web application** is a React + TypeScript single-page application. Its
  unfinished browser work is gated by the accepted desktop Interaction
  Prototype and Workspace View State contract; the final stage-specific Task
  Detail Pane replaces the historical fixed evidence-side-panel assumption. It
  polls active operations and must not reproduce business logic already owned by
  use cases. In production FastAPI serves its compiled static assets; Vite's
  development server proxies `/api` to FastAPI.
- **Operation executor** is an in-process durable runner. It serializes
  state-changing work per workspace, has a small global concurrency cap, and
  persists phase, progress, safe errors, and retry actions. A restart marks
  running work interrupted; queued work may be cancelled, but running work is
  not forcefully interrupted.
- **Evidence index** is a managed local-file boundary below a workspace. Its
  metadata carries workspace, paper, Document Version, Chunk, and serialized
  `SourceAnchor` identities. The production workspace seam receives a real
  embedding collaborator; deterministic collaborators are test-only.

## Deployment Boundary

The first version runs as one native Python process with exactly one Uvicorn
worker. It serves FastAPI, the static web application, and the in-process
executor from a configurable local data directory, and binds to `127.0.0.1` by
default. It has no account system or built-in remote access control, so public
exposure and horizontal replicas are out of scope. Docker/Compose are optional
future packaging, not runtime requirements. A stopped-service copy of the data
directory is the documented backup and migration method.

## Provenance Requirements

Every Claim Citation must preserve enough metadata to let a user inspect the
evidence without guessing:

- workspace and report version
- claim identifier and citation-review state
- selected-paper identifier, title, and source URL or upload record
- document and chunk identifiers
- page and/or section location when parsing provides it
- versioned `SourceAnchor` metadata, including the clean excerpt and parser /
  chunking versions
- source excerpt and retrieval/generation provenance

The PDF-location, workspace/provenance, lifecycle, and topology contracts are
recorded in the closed tickets on the [Wayfinder map](wayfinder/research-paper-workspace.md).

## Compatibility and Legacy

`paper_id`, `content_list_v2.json`, review/outline/chapter packages, generic
query/report endpoints, and the OpenAI developer-doc evaluation corpus are
retained where useful. They must not be deleted through broad mechanical
renames. The former general-RAG phase plan does not define new work; see
[docs/legacy/README.md](legacy/README.md).

## First-Version Non-goals

- account systems, collaboration, and shared workspaces
- scraping or auto-importing paywalled full text
- PDF/Word report export
- presenting a small generic evaluation corpus as enterprise validation
