# Evidence-driven section report generation

Status: Accepted

Date: 2026-07-14

## Context

The initial cited-report slice completed a browser workflow, but it used
lexical retrieval, fixed outline sections, and a templated report generator.
That is useful for structural testing but cannot be presented as the product's
RAG workflow. The product requires an editable Literature Report whose Claims
are traceable to real paper evidence without allowing an unavailable model or
a partial generation to masquerade as a completed report.

## Decision

- A ready Selected Paper has an active Document Version whose Chunks have
  embeddings in a Research Workspace-isolated FAISS index, carrying paper,
  version, Chunk, and SourceAnchor metadata.
- Chunks do not cross parsed title/section boundaries, use an approximately
  500-token maximum and two complete-sentence overlap with Chinese and English
  sentence boundaries, and retain page and character ranges. Tables and
  formulas are not independently embedded in the first version.
- Outline generation first creates a Planning Evidence Bundle: three to five
  topic-and-question queries retrieve vector candidates, which are re-ranked
  with paper-level deduplication and maximal marginal relevance. The bundle has
  roughly twelve to twenty representative Chunks, at most two per paper, and a
  configured external model uses it with the topic and research question to
  propose an editable Report Outline. It returns schema-validated JSON of
  chapters and sections; each section supplies a title, objective,
  expected_claims, and at least one retrieval query. The service assigns
  persistent identities and revision metadata. Its prompt separates system
  rules, task context, bounded planning evidence, and JSON output contract;
  regeneration additionally receives the current outline and explicit user
  instruction, and returns a complete replacement. Planning evidence shapes
  structure and is not body-citation evidence.
- The outline schema requires exactly one first abstract, one or more body
  chapters, one conclusion-and-outlook after the bodies, and exactly one final
  references chapter. Abstract and references have no queries; invalid role
  sets or ordering use the standard one-repair JSON rule.
- Each body section supplies retrieval queries; their results form a bounded
  evidence bundle for the body chapter. The body chapter is the generation and
  scheduling unit. Its external generation model returns structured Claims,
  each naming one or more retrieved Source Chunks or an explicit evidence gap.
  Each query retrieves eight vector candidates; their union is deduplicated and
  MMR-re-ranked to twelve to eighteen Chunks, with at most three from any paper.
  Retained Chunks record the section and query that retrieved them.
  Similarity scores are recorded but no initial fixed threshold represents
  support; the support check decides adequacy. Any future cutoff requires
  calibration against the real ten-paper demonstration rather than a guessed
  value.
- A section with no candidates becomes an evidence gap without a body-model
  call. A body chapter with no evidence for every section completes as an
  all-gap result; otherwise the model receives only the sections with evidence
  and their existing gaps.
- The body-generation prompt separates fixed grounding/JSON-only rules,
  report-and-outline context, the chapter evidence bundle, and the output
  contract. It returns ordered section blocks: every factual block is one
  editable sentence or bullet Claim with proposed Source Chunk IDs; unsupported
  content is an explicit evidence-gap block. Markdown rendering does not alter
  Claim identity or citation binding.
- Report chapters declare roles. Eligible body chapters process independently
  in bounded parallelism, with a deployment-configurable default of two chapter
  workers; each chapter performs retrieval, generation, verification, and its
  possible regeneration serially. Conclusion-and-outlook waits for body results
  and may retrieve only for its outlook; abstract waits for the completed report
  and uses neither retrieval nor citations; references are deterministically
  rendered from the attempt's ready Evidence Coverage without retrieval or a
  model call. Every covered paper appears as either cited or consulted-but-
  uncited, while only cited papers have clickable body citations.
- Verified body citations use first-appearance `[n]` numbering. References use
  that numbering and append consulted-but-uncited papers with their status;
  Chinese reports use GB/T 7714 field ordering and English reports a
  corresponding numbered English rendering. Missing metadata is omitted rather
  than invented.
- The final synthesis model does not rewrite, reorder, or otherwise polish
  verified body Claims. Any factual change returns to its chapter's retrieval,
  generation, and support-check flow.
- The integration input is immutable verified body Claims, their citations, and
  gaps. It emits a conclusion derived from existing Claim IDs that inherits
  their citations; separately retrieved and validated outlook Claims; and an
  uncited abstract that only compresses verified Claims.
  References are deterministically produced by the service and never enter the
  model output.
- Its JSON contains text and one or more derived Claim IDs for every conclusion
  or abstract entry, and cited Claim or gap entries for outlook. The service
  expands and support-checks inherited conclusion sources; abstract derivation
  is retained internally but never rendered as a citation.
- The service validates Chunk identifiers against that section's retrieval
  result. A separate support-validation model then evaluates each Claim against
  only its proposed chunks. It batches a chapter's isolated Claim checks and
  returns a verdict and reason per Claim. Partially-supported and unsupported
  Claims are regenerated once with that reason and rechecked; only supported
  Claims become verified, and all remaining failures become explicit gaps.
- Chapter progress is durable, but a new Report Draft is published only when
  every required chapter has completed with validated cited Claims or explicit
  evidence gaps as applicable. Failure leaves the previous draft unchanged.
- A Report Operation Attempt freezes the outline, Evidence Coverage, model
  configuration, and chapter evidence bundles. On failure it preserves completed
  chapter results internally; retry runs only failed chapters and downstream
  dependencies. A user-requested regeneration creates a fresh attempt.
- Attempts persist normalized ChapterRuns (role, phase, status, retry count,
  timestamps, safe errors), ChapterEvidenceBundles (query attribution, Chunk
  IDs, scores and MMR order), and ClaimCandidates (proposed Chunk IDs,
  validation and regeneration result). They never retain raw prompts, complete
  paper content, or credentials.
- Production does not silently substitute templates, lexical retrieval, or
  fabricated content for unavailable embeddings or model calls. Deterministic
  collaborators are test seams only; real-provider manual acceptance is a
  delivery requirement. Production uses Alibaba Cloud `text-embedding-v4` and
  `deepseek-v4-flash`; credentials are read only from local
  `DASHSCOPE_API_KEY` and `DEEPSEEK_API_KEY` environment variables and never
  enter snapshots or repository files.
- Every JSON-producing phase validates against its declared schema. The first
  malformed or invalid result gets one repair prompt carrying the validation
  error; a second failure fails the phase. The service neither permissively
  guesses JSON nor falls back to a template.
- Deployment defaults use temperatures 0.3 for planning, 0.2 for body
  generation, 0 for support validation, and 0.2 for integration. Each role has
  an output-token limit; its parameters and prompt-template version are
  snapshotted per attempt, and users do not tune them in the first-version UI.

## Consequences

Report generation is slower and makes several external-model calls, but each
generated Claim has a bounded, inspectable evidence path and a localized retry
unit. The workspace needs model configuration and failure/retry UI, while
tests can stay deterministic through injected model collaborators. Existing
generic FAISS and model clients may be reused only through a workspace-scoped
adapter that preserves the stated provenance boundaries.
