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
- Add configurable report generation for Markdown, JSON, and bullet-summary outputs.
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
- Add a small strategy-comparison CLI surface for chunking / top-k / rerank presets.
- Add an eval API target: `POST /eval/run`.
- Compute retrieval and generation reliability metrics.
- Save artifacts to `data/eval_outputs/<run_id>/`, including `metrics.json`,
  `cases.jsonl`, `failures.jsonl`, and `retrieval_debug.jsonl`.

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

## Phase 5: Evaluation Hardening

Goal:
- Turn the current small-sample eval surface into a final, credible quality bar.

Allowed changes:
- Refine the eval dataset schema only where final evaluation needs it.
- Build a final `40`-case eval dataset from a frozen, tracked, explicitly
  reproducible corpus.
- Freeze a narrow `OpenAI` developer-doc corpus under a tracked directory with a
  provenance manifest.
- Run final eval and strategy comparison against the final dataset.
- Add failure analysis and metric reporting for the final acceptance pass.
- Fix small retrieval, citation, format, or eval-contract gaps needed to reach
  the final quality bar.

Do not:
- Add Docker, Compose, or `.env.example` in this phase.
- Do deployment packaging or cloud-specific deployment.
- Do broad interface churn across already completed phases.
- Expand into a broad public-web benchmark crawl.
- Add hand-authored distractor documents for negative testing.

Completion standard:
- A final eval dataset exists and is reproducible.
- The final corpus is a frozen, in-repo snapshot of `12-18` `OpenAI`
  developer-doc pages or curated excerpts limited to `guides`, `API reference`,
  and a small number of `cookbook/examples`.
- The final dataset is fixed at `40` cases with explicit behavior buckets:
  - `24` `full_answer`
  - `8` `partial_answer`
  - `8` `abstain`
- The final dataset is fixed at these question-shape buckets:
  - `12` single-hop fact, definition, or constraint lookup
  - `10` multi-source or multi-section synthesis
  - `8` parameter, limitation, or prerequisite
  - `6` boundary or comparison
  - `4` high-distraction explicit negative
- The final dataset includes all three output formats with a non-trivial mix.
- Metrics meet the Definition of Done targets:
  `Recall@5 >= 80%`, `citation_hit_rate >= 90%`,
  `unknown_citation_count = 0`, and `format_compliance_rate >= 90%`.
- At least one successful trace and one failure analysis are available for later
  README packaging.
- Strategy comparison still exercises the normal report-generation path while
  varying chunking, top-k, and rerank settings.

Verification:

```bash
python -m pytest -q
python -m app.cli.main eval run --dataset data/eval_samples/final_eval_dataset.jsonl
python -m app.cli.main eval compare --dataset data/eval_samples/final_eval_dataset.jsonl --source-dir data/eval_corpus/openai_devdocs
```

## Phase 6: Deployment and Portfolio Packaging

Goal:
- Make the evaluated system easy to run, inspect, and discuss in interviews.

Allowed changes:
- Add Dockerfile and docker-compose.
- Add `.env.example`.
- Complete `/health`, `/state`, and run visibility surfaces needed for
  deployment and debugging.
- Update README with architecture, quickstart, eval results, demo commands, and
  portfolio-oriented project summary.

Do not:
- Redefine the final evaluation targets from Phase 5.
- Commit local indexes, full corpora, or generated run outputs.
- Add cloud-specific deployment unless the user asks for it.

Completion standard:
- A fresh user can run tests and the minimal demo from documented commands.
- Docker Compose starts the service and `/health` responds.
- README clearly and accurately explains capabilities, evaluation results, and
  current limits for RAG/LLM application roles.

Verification:

```bash
python -m pytest -q
docker compose config
docker compose up --build
README quickstart commands
```

## Phase Discipline

Every phase handoff should include:

- What was changed.
- What was intentionally not changed.
- Test results.
- New risks or cleanup items.
- Which phase should be executed next.
