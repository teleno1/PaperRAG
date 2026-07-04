# PaperRAG

PaperRAG is being refactored from an academic paper review prototype into a
general, trustworthy knowledge-base RAG system.

## Current Status

This repository is still in progress.

What works today:

- Verified test baseline: `python -m pytest -q` with 35 passing tests.
- Current product shape: `PDF papers -> MinerU parse -> chunks -> FAISS index -> outline -> review`.
- Existing entrypoints remain available through the CLI and FastAPI app.

What is not finished yet:

- General first-class ingestion for `TXT` and `Markdown`.
- General cited question-answering and report generation outputs.
- Eval dataset, retrieval metrics, citation metrics, and strategy comparison.
- Final reproducible portfolio/demo packaging.

If any of the unfinished items above matter for your use case, treat the project
as a refactor in progress rather than a completed general RAG system.

## Target Product

The refactor target is a portfolio-grade RAG system that can:

- ingest `PDF`, `TXT`, and `Markdown` documents
- run `clean -> chunk -> embed -> index -> retrieve -> generate`
- produce cited answers or reports in formats such as Markdown and JSON
- trace citations back to `document_id` and `chunk_id`
- evaluate retrieval and output quality with reproducible metrics

The active task list and roadmap define the real finish line:

- [AGENTS.md](AGENTS.md)
- [TASKS.md](TASKS.md)
- [docs/refactor-roadmap.md](docs/refactor-roadmap.md)

## Setup

Install the package:

```bash
pip install -e .
```

Sensitive keys must stay in environment variables, not in
`configs/settings.yaml`.

PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="..."
$env:DASHSCOPE_API_KEY="..."

# Required only for PDF parsing with MinerU
$env:MINERU_API_KEY="..."
```

Bash:

```bash
export DEEPSEEK_API_KEY="..."
export DASHSCOPE_API_KEY="..."

# Required only for PDF parsing with MinerU
export MINERU_API_KEY="..."
```

Non-secret configuration lives in `configs/settings.yaml`.

## Verification

Current baseline verification:

```bash
python -m pytest -q
```

Useful health checks for the current CLI surface:

```bash
python -m app.cli.main health
python -m app.cli.main state
```

## Current CLI Surface

These commands reflect the current paper-review-oriented workflow, not the final
general RAG interface:

```bash
python -m app.cli.main corpus prepare
python -m app.cli.main index build
python -m app.cli.main outline generate --topic "..."
python -m app.cli.main review run --topic "..."
python -m app.cli.main review run-from-outline --outline data/outlines/.../outline.json
python -m app.cli.main state
python -m app.cli.main health
```

Current review outputs are written under:

```text
data/review_outputs/<run_id>/
```

## Current API Surface

Start the API:

```bash
uvicorn app.api.main:app --reload
```

Current routes:

- `POST /corpus/prepare`
- `POST /index/build`
- `POST /outline/generate`
- `POST /review/run`
- `POST /review/run-from-outline`
- `GET /state`
- `GET /health`

These routes are also part of the refactor and should not be read as the final
general RAG API contract.

## Data Policy

Tracked sample data is intentionally minimal during the refactor.

- Put your own local PDFs in `data/papers/` when running the current pipeline.
- Generated indexes, parsed outputs, outlines, and run artifacts stay local.
- The source-controlled data policy is documented in [data/README.md](data/README.md).

## Repository Layout

```text
app/
  api/
  cli/
  core/
  domain/
  infrastructure/
  schemas/
  use_cases/
docs/
data/
tests/
```
