# Evaluation Plan

The project should prove reliability with objective evaluation, not only with a
working demo. This document defines the target eval surface for the refactor.

## Evaluation Goals

The system should be able to answer:

- Did retrieval find the right sources?
- Did generation cite only retrieved sources?
- Did the answer cover expected points?
- Did the requested output format hold?
- How slow, expensive, and failure-prone was the run?

## Target Dataset Format

Future eval data should live in:

```text
data/eval_samples/eval_dataset.jsonl
```

Each line should be one JSON object:

```json
{
  "id": "qa-001",
  "query": "How does the system prevent unsupported citations?",
  "expected_sources": ["doc-architecture#validation", "doc-readme#citation"],
  "answer_points": ["source registry", "unknown source check", "citation validation"],
  "output_format": "markdown",
  "tags": ["citation", "trust"]
}
```

Field meanings:

- `id`: stable case id.
- `query`: user question or report instruction.
- `expected_sources`: source ids, document ids, or section anchors that should be
  retrievable for the query.
- `answer_points`: key facts or concepts that should appear in the answer.
- `output_format`: expected output type, such as `markdown`, `json`, or `bullet_summary`.
- `tags`: optional grouping for analysis.

## Target Metrics

Retrieval metrics:

- `recall_at_5`: whether any expected source appears in top 5.
- `recall_at_10`: whether any expected source appears in top 10.
- `mrr`: reciprocal rank of the first expected source.
- `avg_retrieved_sources`: average number of retrieved chunks used.

Generation and citation metrics:

- `citation_hit_rate`: cited sources that match expected or retrieved sources.
- `unknown_citation_count`: citations not present in retrieved source registry.
- `no_source_assertion_rate`: fact-like claims without citations.
- `answer_point_coverage`: expected answer points covered by the output.
- `format_compliance_rate`: outputs that match requested format.

Operational metrics:

- `avg_latency_ms`.
- `p95_latency_ms`.
- `failure_rate`.
- `avg_prompt_tokens` and `avg_completion_tokens` when available.
- `estimated_cost` when model pricing is configured.

## Target CLI and API

Future CLI:

```bash
python -m app.cli.main eval run --dataset data/eval_samples/eval_dataset.jsonl
```

Future API:

```http
POST /eval/run
```

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
