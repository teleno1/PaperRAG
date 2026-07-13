# PaperRAG

PaperRAG is a single-user research-paper workspace for individual researchers
and graduate students. A user defines a topic, uploads papers or discovers
open-access candidates, selects the evidence set, and produces an editable
literature report whose claims can be traced to the supporting paper chunks.

## Product Direction

```text
topic
  -> upload papers / discover open-access candidates
  -> user selects the evidence set
  -> parse, chunk, and index selected papers
  -> editable outline
  -> cited literature report
  -> click a claim to inspect one or more source excerpts
  -> edit, review, and refresh citations
```

The first version is deliberately bounded:

- one local or single-deployment user; no accounts or collaboration
- online discovery returns candidates; only selected papers are evidence
- only public PDFs are automatically imported; users may upload authorised PDFs
- Chinese or English report language, selected per workspace
- browser-based editing with Markdown export
- a substantive edit to a cited claim marks that citation **pending review**

## Current Status

The repository contains a reusable Python/FastAPI/RAG foundation from the
previous refactor: PDF parsing through MinerU, chunking, FAISS retrieval,
outline/report generation, source validation, CLI commands, and API routes.
The first research-workspace delivery slices now add durable workspace
creation, authorised PDF upload, open-paper candidate discovery, guarded public
PDF import, selected-paper evidence gating, readiness/failure state, a React +
TypeScript preparation UI, same-origin static delivery, and versioned workspace
API routes. The outline/report workflow, claim-level evidence panel, and
citation-review state remain later delivery slices.

The current product-planning source of truth is the local
[research-paper workspace map](docs/wayfinder/research-paper-workspace.md).
It records open decisions before implementation starts.

## Legacy Refactor Materials

The earlier goal—turning PaperRAG into a general knowledge-base RAG system—is
no longer the active product direction. Its phase plan, generic-RAG task index,
and OpenAI developer-document evaluation are preserved as historical and
technical reference in [docs/legacy/README.md](docs/legacy/README.md). They do
not define the current backlog or definition of done.

## Existing Local Foundation

Install the package:

```bash
pip install -e .
```

Secrets belong in environment variables, never in `configs/settings.yaml`:

```powershell
$env:DEEPSEEK_API_KEY="..."
$env:DASHSCOPE_API_KEY="..."
$env:MINERU_API_KEY="..." # only for the current PDF parsing path
$env:OPENALEX_API_KEY="..." # optional server-side discovery quota key
```

Run the existing test baseline and health checks:

```bash
python -m pytest -q
python -m app.cli.main health
python -m app.cli.main state
```

The existing CLI and FastAPI endpoints are compatibility/foundation surfaces,
not the future workspace UI contract. Generated indexes, parsed papers, and run
outputs remain local; see [data/README.md](data/README.md).

## Repository Layout

```text
app/                 current Python application foundation
docs/wayfinder/      active local product-planning map and decision tickets
docs/legacy/         superseded general-RAG plans, task cards, and their index
data/                minimal fixtures and local runtime directories
tests/               current automated tests
```
