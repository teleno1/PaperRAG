# Data Directory Policy

> The frozen OpenAI developer-document corpus and generic evaluation fixtures
> below belong to the legacy general-RAG refactor. They remain tracked test and
> regression assets, not the product corpus for the research-paper workspace.
> See [docs/legacy/README.md](../docs/legacy/README.md).

This repository does not track local research corpora or generated runtime artifacts.

## Source-controlled files

- `data/.gitkeep` keeps the top-level directory present.
- `data/samples/` is the only approved location for tiny curated demo assets.
  Phase 2 adds `data/samples/phase2_corpus/` as a tiny TXT/Markdown sample
  corpus for ingestion and indexing tests.
- `data/eval_samples/` is the approved location for tiny tracked evaluation
  fixtures such as `eval_dataset.jsonl`.
- `data/eval_corpus/openai_devdocs/` is the approved location for the frozen
  Phase 5 final evaluation corpus snapshot and its tracked provenance manifest.

## Local-only files

Keep these paths out of git:

- `data/papers/` for user-provided raw inputs.
- `data/processed_papers/` for parsed MinerU outputs and extracted assets.
- `data/database/` for FAISS indexes and metadata.
- `data/outlines/` for generated outlines.
- `data/review_outputs/` for review and report runs.
- `data/eval_outputs/` for evaluation artifacts.

If you need to run the current paper-review pipeline locally, place your own PDFs in
`data/papers/` and let the application regenerate the downstream artifacts.
