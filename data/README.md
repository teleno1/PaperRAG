# Data Directory Policy

This repository does not track local research corpora or generated runtime artifacts.

## Source-controlled files

- `data/.gitkeep` keeps the top-level directory present.
- `data/samples/` is the only approved location for tiny curated demo assets.
  Phase 0 keeps it empty until a later task adds a reproducible cross-format sample corpus.

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
