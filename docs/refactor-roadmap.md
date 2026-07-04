# PaperRAG Refactor Roadmap

This roadmap exists to keep the refactor incremental. Future agents should work
on one phase at a time and stop after verification. Do not jump ahead unless the
user explicitly asks for a roadmap revision.

## Target Product

Refactor PaperRAG from an academic paper review pipeline into a general,
trustworthy knowledge-base RAG system:

```text
documents -> parsing -> chunks -> vector index -> cited answers/reports -> eval -> deploy
```

The end result should be suitable for a resume and GitHub portfolio: clear
architecture, reproducible setup, objective evaluation, and deployable API.

## Phase 0: Repository Slimming and Context Setup

Goal:
- Make the repository safe and readable before changing core behavior.

Allowed changes:
- Add project context files.
- Update `.gitignore` for generated data, indexes, parsed corpora, run outputs,
  and eval outputs.
- Move or remove tracked sample artifacts only after confirming the exact paths
  and preserving a tiny demo sample if needed.
- Update README to explain the refactor direction.

Do not:
- Rewrite ingestion, indexing, retrieval, or generation logic.
- Rename core Python packages.
- Delete data blindly.

Completion standard:
- `AGENTS.md` and `docs/` context files exist.
- Generated/local artifacts are clearly separated from source-controlled sample
  data.
- Tests pass.

Verification:

```bash
python -m pytest -q
git status --short
```

## Phase 1: Introduce Document-Centric Domain Models

Goal:
- Add general concepts while keeping old paper-specific flow working.

Allowed changes:
- Add `DocumentMetadata`, `DocumentChunk`, `Source`, and related models.
- Add adapters from existing `PaperMetadata`/`Chunk` metadata to document-style
  metadata.
- Start replacing internal metadata keys with general equivalents:
  `document_id`, `source_id`, `source_path`, `section`, `content`.
- Keep compatibility fields such as `paper_id` where existing tests/routes still
  need them.

Do not:
- Delete `review`, `outline`, or `chapter` pipeline code yet.
- Break existing FAISS metadata loading.
- Do broad mechanical renames across all files in one step.

Completion standard:
- New document models are covered by tests.
- Existing tests still pass.
- Existing review pipeline still runs with compatibility metadata.

Verification:

```bash
python -m pytest -q
```

## Phase 2: General Ingestion

Goal:
- Support Markdown, TXT, and PDF as first-class document inputs.

Allowed changes:
- Introduce a parser interface for document inputs.
- Add Markdown and TXT parsers.
- Keep MinerU PDF parsing as one PDF parser implementation.
- Produce a normalized intermediate representation before chunking.
- Update config paths from paper-specific names toward document/corpus names
  while preserving compatibility.

Do not:
- Remove MinerU support.
- Require external API calls for Markdown/TXT ingestion.
- Force all users to have PDF parsing credentials for non-PDF workflows.

Completion standard:
- A small Markdown/TXT sample corpus can be indexed without MinerU.
- Tests cover parser selection and normalized chunks.
- Existing PDF-oriented tests still pass or are intentionally migrated.

Verification:

```bash
python -m pytest -q
python -m app.cli.main health
```

## Phase 3: General Answer and Report Generation

Goal:
- Replace the academic-review-only product surface with general RAG outputs.

Allowed changes:
- Add query/answer use cases that retrieve sources and produce cited answers.
- Add configurable report generation for Markdown/JSON outputs.
- Keep old review commands temporarily as compatibility or mark them deprecated.
- Add API routes for query and report generation.

Do not:
- Build a frontend.
- Remove citation validation.
- Make prompts depend on one academic domain.

Completion standard:
- CLI can run a cited answer flow against an existing index.
- API exposes query/report endpoints.
- Outputs include source ids that can be traced to retrieved chunks.

Verification:

```bash
python -m pytest -q
python -m app.cli.main health
```

## Phase 4: Trustworthy Evaluation

Goal:
- Prove the project is more than a working demo.

Allowed changes:
- Add `eval_dataset.jsonl` support.
- Add an eval CLI target: `python -m app.cli.main eval run`.
- Add an eval API target: `POST /eval/run`.
- Compute retrieval and generation reliability metrics.
- Save metrics to `data/eval_outputs/<run_id>/metrics.json`.

Do not:
- Use LLM-only subjective judging as the only metric.
- Hide failed examples.
- Require paid API calls for every unit test.

Completion standard:
- Eval can run on a small sample dataset.
- Metrics include Recall@5, MRR, citation hit rate, unsupported claim rate or
  no-source assertion rate, format compliance, average latency, and failure rate.
- README shows a metrics table and at least one failure analysis example.

Verification:

```bash
python -m pytest -q
python -m app.cli.main eval run --dataset data/eval_samples/eval_dataset.jsonl
```

## Phase 5: Deployment and Portfolio Packaging

Goal:
- Make the project easy to run, inspect, and discuss in interviews.

Allowed changes:
- Add Dockerfile and docker-compose.
- Add `.env.example`.
- Add `/health`, `/state`, and metrics or run-history endpoints if missing.
- Update README with architecture diagram, quickstart, eval results, and demo
  commands.
- Add lightweight sample data that is small enough for git.

Do not:
- Commit local indexes, full corpora, or generated run outputs.
- Add cloud-specific deployment unless the user asks for it.
- Make setup depend on hidden local paths.

Completion standard:
- A fresh user can run tests and start the API from documented commands.
- Docker Compose starts the service and `/health` responds.
- README clearly explains what the project proves for RAG/LLM application roles.

Verification:

```bash
python -m pytest -q
docker compose up --build
```

## Phase Discipline

Every phase handoff should include:

- What was changed.
- What was intentionally not changed.
- Test results.
- New risks or cleanup items.
- Which phase should be executed next.

