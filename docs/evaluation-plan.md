# Legacy: Generic-RAG Evaluation Plan

> **Historical evaluation asset.** This plan and its recorded results evaluate
> the former generic-RAG direction on a small frozen OpenAI developer-document
> corpus. They demonstrate reusable retrieval and citation-validation work, but
> do not establish real-world or enterprise-scale product quality.
>
> The research-paper workspace will define product acceptance around selected
> papers, claim-level traceability, citation-review states, and an end-to-end
> user workflow through its [active Wayfinder map](wayfinder/research-paper-workspace.md).
> This document remains unchanged below as an auditable historical record.

The project should prove reliability with objective evaluation, not only with a
working demo. This document defines the target eval surface for the refactor.

## Evaluation Goals

The system should be able to answer:

- Did retrieval find the right sources?
- Did generation cite only retrieved sources?
- Did the answer cover expected points?
- Did the requested output format hold?
- How slow, expensive, and failure-prone was the run?

## Phase 5 Final Eval Contract

Phase 4 proved that the eval runner, metrics, and strategy-comparison surfaces
work on small tracked fixtures. Phase 5 tightens that into a final,
resume-quality evaluation asset with a frozen corpus, explicit negative
protocol, and reproducible acceptance metrics.

### Final Corpus Boundary

The final evaluation corpus should be a small, frozen, in-repo snapshot:

- Source ecosystem: `OpenAI` developer documentation only.
- Scope: `12-18` source documents.
- Tracked source directory target: `data/eval_corpus/openai_devdocs/`.
- Tracked manifest target: `data/eval_corpus/openai_devdocs/manifest.json`.
- Allowed document types:
  - `guides`
  - `API reference`
  - a small number of `cookbook/examples`
- Allowed topic surface:
  - `Responses`
  - `structured outputs`
  - `function calling`
  - `embeddings`
  - `vector-store` or file-search-adjacent developer docs
- Out of scope:
  - pricing, marketing, blog, or newsroom pages
  - broad product overviews not needed for the eval contract
  - dynamic or unfrozen web lookups during acceptance
  - hand-authored distractor documents
  - full-site mirrors or bulk crawls that make provenance review impractical

The purpose of this boundary is to keep the corpus narrow enough to annotate
well, but realistic enough to surface true retrieval and grounding failures.

Recommended document-type mix inside the `12-18` source-document budget:

- `4-6` guides
- `5-7` API reference pages
- `2-4` cookbook or example pages

Each frozen source document should be a curated snapshot or excerpt file rather
than a raw site mirror. The corpus manifest should record, at minimum:

- `doc_id`
- original URL
- snapshot date
- included sections or excerpt notes
- why the document is in scope for final evaluation

### Final Dataset Shape

The final Phase 5 dataset target is fixed at `40` cases:

- `24` `full_answer`
- `8` `partial_answer`
- `8` `abstain`

Output-format buckets should also be fixed:

- `20` `markdown`
- `10` `json`
- `10` `bullet_summary`

Question-shape buckets are also fixed:

- `12` single-hop fact, definition, or constraint lookup cases
- `10` multi-source or multi-section synthesis cases
- `8` parameter, limitation, or prerequisite cases
- `6` boundary or comparison cases
- `4` high-distraction explicit negative cases

These are two separate axes:

- `answer_expectation` controls how the system should behave.
- question-shape buckets control what kind of reasoning or retrieval challenge
  the case presents.

## Target Dataset Format

Future eval data should live in:

```text
data/eval_samples/final_eval_dataset.jsonl
```

Phase 4 already established the loader and manual eval flow with a tiny tracked
sample fixture. Phase 5 should add the final frozen corpus and a final dataset
of `40` cases as separate tracked assets rather than overwriting the Phase 4
sample fixture assumptions.

Each line should be one JSON object:

```json
{
  "id": "qa-001",
  "query": "How does the system prevent unsupported citations?",
  "answer_expectation": "full_answer",
  "question_shape": "single_hop",
  "expected_sources": ["doc-architecture#validation", "doc-readme#citation"],
  "answer_points": ["source registry", "unknown source check", "citation validation"],
  "unsupported_aspects": [],
  "output_format": "markdown",
  "tags": ["citation", "trust"]
}
```

Field meanings:

- `id`: stable case id.
- `query`: user question or report instruction.
- `answer_expectation`: expected response mode. Phase 5 should constrain this to
  `full_answer`, `partial_answer`, or `abstain`.
- `question_shape`: required case-shape bucket. Phase 5 should constrain this to
  `single_hop`, `multi_source_synthesis`, `parameter_constraint`,
  `boundary_comparison`, or `high_distraction_negative`.
- `expected_sources`: source ids, document ids, or section anchors that should be
  retrievable for the query. For negative cases, these are the nearby or
  boundary-defining sources a grounded refusal or partial answer should rely on.
- `answer_points`: key facts or concepts that should appear in the answer. For
  `abstain` cases, this should be an empty list.
- `unsupported_aspects`: aspects that must not be hallucinated as supported.
  For `partial_answer`, this must be non-empty. For `full_answer`, it should be
  empty. For `abstain`, it should capture the requested information that the
  corpus cannot support.
- `output_format`: expected output type, such as `markdown`, `json`, or `bullet_summary`.
- `tags`: optional grouping for analysis.

Phase 5 should keep gold evidence at `source_id` granularity. The eval dataset
must not require sentence-level or span-level annotation.

Phase 5 schema-validation rules should include at least:

- `expected_sources` should be non-empty for all final dataset cases.
- `answer_points` should be non-empty for `full_answer` and `partial_answer`.
- `answer_points` should be empty for `abstain`.
- `unsupported_aspects` should be empty for `full_answer`.
- `unsupported_aspects` should be non-empty for `partial_answer` and `abstain`.

Phase 5 implementation should enforce those rules in the loader and preserve
the resulting fields into `cases.jsonl` and `failures.jsonl` so case-level
failure analysis is explainable without reopening the dataset file by hand.

### Case Authoring Rules

Phase 5 case authoring should follow these rules:

- Write queries as plausible user requests, not as page-title lookups.
- Keep each case grounded in `1-3` primary `expected_sources` whenever
  possible; use more only when multi-source synthesis genuinely requires it.
- Do not write cases about pricing, release timing, or fast-changing product
  news.
- Do not rely on hidden annotator knowledge that is absent from the frozen
  corpus.
- Prefer questions that test retrieval boundaries, citation grounding, or
  format compliance over trivia that can be guessed from model priors.
- For `abstain` and `partial_answer` cases, make the insufficiency legible from
  nearby or boundary-defining corpus documents.

### Negative Protocol

Negative and low-evidence cases must be explicit in the dataset contract.

- `full_answer`: the corpus contains enough evidence to answer the query
  directly and support the expected answer points.
- `abstain`: the corpus does not contain sufficient evidence for the requested
  answer, and the correct behavior is to refuse or clearly state that the
  information is unavailable in the corpus.
- `partial_answer`: the corpus contains some relevant evidence but not enough to
  support a complete answer. The correct behavior is to answer only the
  supported portion and explicitly note what remains unsupported or unknown.

Important nuance:

- `abstain` does not mean the system should answer from nowhere.
- `abstain` cases should still be attached to nearby or boundary-defining
  `expected_sources` so retrieval and grounded refusal can be evaluated.
- `partial_answer` cases should have both supported answer points and explicit
  unsupported aspects so the evaluation can detect overclaiming.

Important boundary:

- Runtime system behavior must not depend on the gold labels.
- `answer_expectation`, `expected_sources`, and other annotations are for
  offline evaluation only.
- Negative examples should come from naturally confusing or low-evidence slices
  inside the frozen corpus, not from artificial distractor documents.

## Target Metrics

Retrieval metrics:

- `recall_at_5`: whether any expected source appears in top 5.
- `recall_at_10`: whether any expected source appears in top 10.
- `mrr`: reciprocal rank of the first expected source.
- `avg_retrieved_sources`: average number of unique retrieved source ids after
  deterministic normalization/deduplication.

Generation and citation metrics:

- `citation_hit_rate`: cited sources that match expected or retrieved sources.
- `unknown_citation_count`: citations not present in retrieved source registry.
- `no_source_assertion_rate`: fact-like claims without citations.
- `answer_point_coverage`: expected answer points covered by the output.
- `unsupported_aspect_violation_count`: unsupported aspects repeated or claimed
  as supported in the output.
- `abstention_cue_rate`: share of cases whose output contains an explicit
  abstention cue such as "not documented" or "insufficient information".
- `format_compliance_rate`: outputs that match requested format.

For Phase 4, citation and format checks should stay deterministic:

- `citation_hit_rate` may credit ids that match expected sources even when
  retrieval missed them; pair it with `unknown_citation_count` to surface
  unsupported citations against the retrieved registry.
- JSON compliance should use real JSON parsing plus report-shape checks.
- Markdown and `bullet_summary` compliance should use simple structural checks.
- `no_source_assertion_rate` should use a deterministic heuristic, not an LLM judge.

Phase 5 acceptance should emphasize:

- `Recall@5 >= 80%`
- `citation_hit_rate >= 90%`
- `unknown_citation_count = 0`
- `format_compliance_rate >= 90%`
- strategy comparison should reuse the same report-generation path as `eval run`
  rather than a synthetic or extractive-only comparison reporter

Phase 5 failure analysis should distinguish at least:

- retrieval miss
- citation or source-registry failure
- format-compliance failure
- unsupported assertion
- abstention failure
- partial-answer failure

Recommended case-level failure labels:

- `retrieval_miss`
- `citation_registry_failure`
- `format_failure`
- `unsupported_assertion`
- `abstention_failure`
- `partial_answer_failure`

Operational metrics:

- `avg_latency_ms`.
- `p95_latency_ms`.
- `failure_rate`.
- `avg_prompt_tokens` and `avg_completion_tokens` when available.
- `estimated_cost` when model pricing is configured.

## Target CLI and API

Future CLI:

```bash
python -m app.cli.main eval run --dataset data/eval_samples/final_eval_dataset.jsonl
python -m app.cli.main eval compare --dataset data/eval_samples/final_eval_dataset.jsonl --source-dir data/eval_corpus/openai_devdocs
```

Future API:

```http
POST /eval/run
```

Phase 4 eval generation should route through the report use case so the dataset
`output_format` maps directly onto the existing `markdown`, `json`, and
`bullet_summary` report contract.
By default, eval runs should exercise the currently configured retrieval/index
surface rather than swapping in a hidden sample-only corpus.

Target output directory:

```text
data/eval_outputs/<run_id>/
  metrics.json
  cases.jsonl
  failures.jsonl
  retrieval_debug.jsonl
```

`metrics.json` should be the resume-friendly artifact. `failures.jsonl` should
make debugging honest and repeatable.

For small strategy studies, Phase 4 can reindex the tracked sample corpus under
explicit chunking/rerank presets so comparisons stay reproducible and
inspectable.

For Phase 5, the final acceptance dataset should run on the frozen final corpus
under `data/eval_corpus/openai_devdocs` rather than the Phase 2 sample
fixtures.

## Testing Rules

- Unit tests should use fake embedding, retrieval, and LLM clients.
- Tests must not require paid API calls.
- Eval command tests can run on tiny fixtures.
- Metrics calculations should be deterministic.
- Failed examples should remain inspectable instead of being swallowed.

## README Reporting Target

The final portfolio README should include:

```text
Evaluation summary
- Dataset size: N cases
- Recall@5: X%
- Citation hit rate: Y%
- Format compliance: Z%
- Average latency: T ms
- Top failure modes: ...
```

Also include one successful trace and one failed case with the lesson learned.
That makes the project look engineered instead of merely demoed.

## Phase 5 Final Results

Acceptance run executed on `2026-07-10`:

- Command:
  `python -m app.cli.main eval run --dataset data/eval_samples/final_eval_dataset.jsonl`
- Run id: `20260710_190826_efc6c4`
- Dataset: `40` cases on the frozen `data/eval_corpus/openai_devdocs/` corpus

Final acceptance metrics:

- `Recall@5`: `1.00`
- `Recall@10`: `1.00`
- `MRR`: `0.9625`
- `citation_hit_rate`: `1.00`
- `unknown_citation_count`: `0`
- `format_compliance_rate`: `1.00`
- `answer_point_coverage`: `0.7521`
- `unsupported_aspect_violation_count`: `5`
- `abstention_cue_rate`: `0.40`
- `failure_rate`: `0.20`
- `avg_latency_ms`: `22414.53`
- `p95_latency_ms`: `39195.14`

These meet the Phase 5 Definition of Done thresholds for retrieval, citation
registry safety, and output-format compliance.

### Successful Trace

Representative success case: `qa-028`

- Query asks for a partial answer about vector store file batches plus a clear
  boundary note about whether the corpus documents a recommended polling
  backoff schedule.
- Retrieval found the expected `vector-stores-file-batches` evidence and nearby
  boundary-defining support from `vector-stores-overview`,
  `vector-stores-search`, and `file_search_responses`.
- The output separated supported facts from unsupported details:
  - supported: file batches add multiple files to a vector store and are a
    store-population step
  - unsupported: the corpus does not document a recommended polling backoff
    schedule
- Result: pass with `citation_hit_rate = 1.0`, `format_compliance = 1.0`,
  `answer_point_coverage = 1.0`, `unsupported_aspect_violation_count = 0`, and
  `abstention_cue_present = true`.

### Failure Analysis

Representative failure cluster: `qa-037` and `qa-038`

- Both are `abstain` cases from the frozen high-distraction-negative bucket.
- Retrieval succeeded and citation validation stayed clean.
- The failures came from the model restating unsupported topics too directly in
  the answer body, which the deterministic checker still counts as
  `unsupported_assertion` even when the answer is mostly refusal-shaped.
- Example lesson: refusals about out-of-scope topics still need tighter wording
  so they do not read like the corpus is affirmatively making claims about that
  unsupported topic.

Remaining failures in the acceptance run are concentrated in:

- multi-source `full_answer` cases that miss one required answer point
- `partial_answer` or `abstain` cases where the output names the unsupported
  topic too assertively

## Phase 5 Strategy Comparison

Comparison run executed on `2026-07-10`:

- Command:
  `python -m app.cli.main eval compare --dataset data/eval_samples/final_eval_dataset.jsonl --source-dir data/eval_corpus/openai_devdocs`
- Run id: `20260710_192339_c86c53`

This run reindexed the frozen corpus for each chunking / top-k / rerank preset
while keeping the normal report-generation path in place.

Headline comparison results:

- Best failure rate: `0.325`
  - `balanced_topk5_rerank_on`
  - `fine_grained_topk3_rerank_on`
- Best citation hit rate: `1.00` on several strategies
- Lowest retrieval score in the matrix:
  `fine_grained_topk5_rerank_on` at `Recall@5 = 0.975`

Comparison takeaway:

- reranking helped the balanced presets more consistently than simply lowering
  or raising `top_k`
- the production acceptance run on the current default stack still outperformed
  every comparison preset on overall failure rate (`0.20` vs `0.325+`)
