# PaperRAG Architecture Notes

This document records the current architecture and the intended target
architecture. It is meant to help future agents avoid accidental rewrites.

## Current System Shape

Current flow:

```text
PDF papers
  -> MinerU parsing
  -> content_list_v2.json
  -> ChunkBuilder
  -> DashScope embeddings
  -> FAISS index + metadata.json
  -> retrieval/rerank
  -> outline generation
  -> chapter drafts
  -> final review export
  -> citation validation
```

Current package structure:

```text
app/
  api/              FastAPI app and routes
  cli/              argparse CLI entrypoint
  core/             config, paths, logging, exceptions
  domain/           business models and pipeline rules
  infrastructure/   external services: LLMs, parsing, vector store, exporters
  schemas/          API request/response models
  use_cases/        application-level orchestration
tests/              unit and integration-style tests with fakes
configs/            non-secret YAML settings and env examples
data/               currently contains local corpora and generated artifacts
```

## Reusable Modules

Keep and evolve these unless a roadmap phase explicitly replaces them:

- `app/core`
  - Config loading already supports YAML plus environment overrides.
  - Secrets are intentionally kept out of YAML.
- `app/api` and `app/cli`
  - These are valuable portfolio surfaces and should remain first-class.
- `app/infrastructure/llm`
  - Existing DeepSeek/DashScope clients can back general RAG.
  - Network calls should stay mockable in tests.
- `app/infrastructure/vectorstore`
  - FAISS persistence and metadata handling are reusable.
  - `IndexBuilder` can now index either legacy MinerU JSON outputs or a tiny
    parser-driven TXT/Markdown source corpus for tests.
- `app/infrastructure/chunking`
  - Chunk sizing, overlap, and section-aware splitting are useful.
- `app/domain/validation`
  - Citation/source validation should become a general trust layer.

## Current Coupling Points

These concepts are too paper/review-specific and should be reduced gradually:

- `paper_id`, `PaperMetadata`, `papers_dir`, `processed_papers`.
- `title`, `authors`, `year`, `venue` as required metadata.
- `review`, `outline`, `chapter`, `final_pass`, `abstract`, `summary_outlook`.
- `content_list_v2.json` as the only processed input.
- MinerU as the only ingestion path.
- Generated `data/` artifacts tracked as if they were source files.

Do not remove these in one broad pass. Add general abstractions first, then
adapt the old pipeline or retire it phase by phase.

## Target Concepts

Use these names for new general RAG work:

- `Document`
  - A user-provided source file or text object.
  - Has `document_id`, `source_path`, `source_type`, `title`, optional metadata.
- `DocumentChunk`
  - Searchable text span derived from a document.
  - Has `chunk_id`, `document_id`, `section`, `content`, token estimate, metadata.
- `ParsedDocument` / `ParsedDocumentUnit`
  - Normalized parser output before chunking.
  - Units preserve raw content plus optional section/page metadata across PDF,
    TXT, and Markdown ingestion.
- `Source`
  - A retrieved chunk exposed to generation and citation validation.
  - Has stable `source_id`, chunk metadata, score, and original content.
- `Query`
  - User intent plus retrieval/generation options.
- `Answer`
  - Cited response with source ids and optional structured output.
- `Report`
  - Longer generated artifact with sections and citations.
- `EvaluationRun`
  - A reproducible run over an eval dataset with metrics and failed cases.

## Layering Rules

- `domain`
  - Pure business models and rules.
  - No FastAPI imports.
  - No direct filesystem, HTTP, or API-key access.
- `use_cases`
  - Orchestrates domain and infrastructure.
  - Owns high-level workflows such as ingest, index, answer, report, eval.
  - The new general query flow is `retrieve -> structured cited answer -> cited-source validation`.
- `infrastructure`
  - Implements parsers, embedding clients, rerankers, vector stores, exporters.
  - External services must be injectable or replaceable in tests.
- `api`
  - Thin request/response translation only.
  - No complex business logic.
- `cli`
  - Thin command parsing and output formatting.
  - Call use cases instead of duplicating logic.

## Compatibility Strategy

- Prefer adapters over immediate deletion.
- Keep old review routes/commands until replacement query/report flows are
  tested and documented.
- Metadata can temporarily include both `document_id` and `paper_id`.
- Tests should lock behavior before and after each migration step.

## Desired End-State Flow

```text
Markdown/TXT/PDF documents
  -> parser interface
  -> ParsedDocument / ParsedDocumentUnit
  -> DocumentChunk
  -> embeddings
  -> vector index
  -> retrieval + rerank
  -> structured cited answer/report
  -> retrieved-source id validation
  -> citation validation
  -> eval metrics
  -> deployable API/CLI
```
