# Final Eval Dataset Notes

This dataset is the fixed Phase 5 evaluation asset for PaperRAG.

- Corpus boundary: `data/eval_corpus/openai_devdocs/`
- Snapshot date: `2026-07-10`
- Source ecosystem: OpenAI developer docs and a small cookbook slice
- Case count: `40`
- Answer expectation mix: `24 full_answer / 8 partial_answer / 8 abstain`
- Output format mix: `20 markdown / 10 json / 10 bullet_summary`
- Question-shape mix:
  - `12` `single_hop`
  - `10` `multi_source_synthesis`
  - `8` `parameter_constraint`
  - `6` `boundary_comparison`
  - `4` `high_distraction_negative`

Authoring rules:

- Queries are phrased as plausible user requests rather than title lookups.
- `expected_sources` always point into the frozen corpus.
- `partial_answer` and `abstain` rows use `unsupported_aspects` to make the
  unsupported boundary explicit.
