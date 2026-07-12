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
  -> parse PDFs while retaining source locations
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
- `CitationReviewState`: verified or pending review. Substantive claim edits
  invalidate the verified status without deleting evidence history.

## Architectural Boundaries

- **Domain** owns workspace, paper-selection, report, citation, and review-state
  rules; it has no FastAPI, filesystem, or HTTP dependency.
- **Use cases** orchestrate discovery, upload/import, parsing/indexing, outline
  approval, generation, citation refresh, and report export.
- **Infrastructure** implements MinerU-compatible parsing, source-location
  extraction, embeddings, FAISS, LLM calls, open-paper discovery adapters, and
  local persistence. External services remain injectable for tests.
- **API** exposes thin workspace-oriented operations and progress/state
  reporting. Existing generic routes remain compatibility endpoints until
  product tickets replace or adapt them.
- **Web application** is the primary first-version surface. It presents the
  workspace workflow, report editor, evidence side panel, and citation-review
  state; it must not reproduce business logic already owned by use cases.

## Provenance Requirements

Every Claim Citation must preserve enough metadata to let a user inspect the
evidence without guessing:

- workspace and report version
- claim identifier and citation-review state
- selected-paper identifier, title, and source URL or upload record
- document and chunk identifiers
- page and/or section location when parsing provides it
- source excerpt and retrieval/generation provenance

The PDF-location and workspace/provenance contracts remain open planning work;
see the [Wayfinder map](wayfinder/research-paper-workspace.md).

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
