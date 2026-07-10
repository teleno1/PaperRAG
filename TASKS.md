# TASKS

This is the short execution index for the PaperRAG refactor. Detailed task
cards live under `docs/tasks/` by phase so Codex does not need to load the full
backlog every time.

## Project Goal

Refactor the existing PaperRAG thesis prototype into a reproducible, general,
trustworthy knowledge-base RAG system.

The finished project must support at least `PDF`, `TXT`, and `Markdown`
documents; clean and chunk documents; embed chunks into a vector index; retrieve
context for a user query; generate the requested output format; trace answer
citations back to source document chunks; and evaluate different chunking,
retrieval, and reranking strategies.

## Definition of Done

The project is not complete unless all of the following are true:

- It supports `PDF`, `TXT`, and `Markdown` ingestion.
- It can run the full flow: clean -> chunk -> embed -> index -> retrieve ->
  generate cited answer/report.
- Each answer citation can be traced to a source `document_id` and `chunk_id`.
- It includes an eval dataset with at least 30 questions.
- It reaches `Recall@5 >= 80%` on the eval dataset.
- It reaches `citation_hit_rate >= 90%`.
- It reaches `unknown_citation_count = 0`.
- It reaches output `format_compliance_rate >= 90%`.
- It can compare chunking, retrieval, and reranking strategies with metrics.
- A fresh environment can reproduce the minimal demo from README commands.

For execution rules, see [AGENTS.md](AGENTS.md).

## Active Task

Current: `T5-02`

Details: [docs/tasks/phase-5.md](docs/tasks/phase-5.md)

## Phase Task Files

| Phase | File | Purpose |
|------|------|---------|
| Phase 0 | [docs/tasks/phase-0.md](docs/tasks/phase-0.md) | Repo slimming and context setup |
| Phase 1 | [docs/tasks/phase-1.md](docs/tasks/phase-1.md) | Document-centric domain models |
| Phase 2 | [docs/tasks/phase-2.md](docs/tasks/phase-2.md) | General ingestion |
| Phase 3 | [docs/tasks/phase-3.md](docs/tasks/phase-3.md) | Cited answers and reports |
| Phase 4 | [docs/tasks/phase-4.md](docs/tasks/phase-4.md) | Evaluation and strategy comparison |
| Phase 5 | [docs/tasks/phase-5.md](docs/tasks/phase-5.md) | Evaluation hardening and final quality validation |
| Phase 6 | [docs/tasks/phase-6.md](docs/tasks/phase-6.md) | Deployment and portfolio packaging |

## Status Overview

| Task | Status | Details |
|------|--------|---------|
| T0-01 | done | [Phase 0](docs/tasks/phase-0.md#t0-01-update-gitignore-for-generated-artifacts) |
| T0-02 | done | [Phase 0](docs/tasks/phase-0.md#t0-02-audit-and-slim-data) |
| T0-03 | done | [Phase 0](docs/tasks/phase-0.md#t0-03-update-readme-with-the-refactor-direction) |
| T1-01 | done | [Phase 1](docs/tasks/phase-1.md#t1-01-add-document-centric-domain-models) |
| T1-02 | done | [Phase 1](docs/tasks/phase-1.md#t1-02-add-compatibility-adapters-for-old-paper-models) |
| T1-03 | done | [Phase 1](docs/tasks/phase-1.md#t1-03-add-document-metadata-to-vector-index-records) |
| T2-01 | done | [Phase 2](docs/tasks/phase-2.md#t2-01-define-a-general-parser-interface) |
| T2-02 | done | [Phase 2](docs/tasks/phase-2.md#t2-02-implement-txt-and-markdown-parsers) |
| T2-03 | done | [Phase 2](docs/tasks/phase-2.md#t2-03-wrap-mineru-as-the-pdf-parser) |
| T2-04 | done | [Phase 2](docs/tasks/phase-2.md#t2-04-index-a-tiny-txtmarkdown-sample-corpus) |
| T3-01 | done | [Phase 3](docs/tasks/phase-3.md#t3-01-add-cited-answer-use-case) |
| T3-02 | done | [Phase 3](docs/tasks/phase-3.md#t3-02-add-report-generation-use-case) |
| T3-03 | done | [Phase 3](docs/tasks/phase-3.md#t3-03-add-cliapi-query-and-report-entrypoints) |
| T4-01 | done | [Phase 4](docs/tasks/phase-4.md#t4-01-add-eval-dataset-format-and-loader) |
| T4-02 | done | [Phase 4](docs/tasks/phase-4.md#t4-02-implement-retrieval-metrics) |
| T4-03 | done | [Phase 4](docs/tasks/phase-4.md#t4-03-implement-citation-and-output-metrics) |
| T4-04 | done | [Phase 4](docs/tasks/phase-4.md#t4-04-add-eval-cli-api-and-output-artifacts) |
| T4-05 | done | [Phase 4](docs/tasks/phase-4.md#t4-05-add-strategy-comparison) |
| T5-01 | done | [Phase 5](docs/tasks/phase-5.md#t5-01-add-final-eval-dataset-plan-and-schema-refinements) |
| T5-02 | todo | [Phase 5](docs/tasks/phase-5.md#t5-02-build-final-40-case-eval-dataset) |
| T5-03 | todo | [Phase 5](docs/tasks/phase-5.md#t5-03-run-final-eval-analyze-failures-and-tighten-quality) |
| T5-04 | todo | [Phase 5](docs/tasks/phase-5.md#t5-04-final-evaluation-acceptance) |
| T6-01 | todo | [Phase 6](docs/tasks/phase-6.md#t6-01-add-deployment-files) |
| T6-02 | todo | [Phase 6](docs/tasks/phase-6.md#t6-02-complete-healthstate-and-run-visibility) |
| T6-03 | todo | [Phase 6](docs/tasks/phase-6.md#t6-03-update-readme-for-portfolio-presentation) |
| T6-04 | todo | [Phase 6](docs/tasks/phase-6.md#t6-04-final-deployment-and-portfolio-acceptance) |
