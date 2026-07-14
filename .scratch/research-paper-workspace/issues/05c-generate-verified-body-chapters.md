# 05C — Generate Verified Body Chapters

**What to build:** A researcher can start a Report Operation Attempt from an
approved Report Outline and see real, recoverable body-chapter generation:
section queries retrieve evidence, independent chapters run in bounded
parallelism, and every factual Claim is grounded and support-checked before it
can be used by final report assembly.

**Blocked by:** 05B — Generate an Evidence-Driven Report Outline.

**Status:** ready-for-agent

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

- [ ] Every body-section query retrieves eight vector candidates; each body
  chapter deduplicates and MMR-reranks to a 12–18 Chunk Chapter Evidence Bundle
  with at most three Chunks per paper and retained section/query attribution.
  Empty sections become explicit evidence gaps without an LLM call.
- [ ] Up to two independent body chapters run concurrently while each chapter
  serially retrieves, generates structured section blocks, validates source IDs,
  support-checks Claims, and regenerates a partially supported or unsupported
  Claim at most once. A valid Claim is a sentence or bullet with one or more
  proposed Chunk IDs; remaining failures become evidence gaps.
- [ ] The browser/API show per-chapter queued/running/validating/failed state,
  safe errors, evidence gaps, and retry actions. The Attempt persists frozen
  inputs, ChapterRuns, normalized Evidence Bundles, Claim candidates, verdicts,
  and retry counts, but does not publish these provisional results as a Report
  Draft.
- [ ] A retry reuses successful chapter results and reruns only failed chapters;
  controlled tests cover isolation, scheduling, validation, and recovery. A
  documented real-provider manual acceptance run demonstrates actual body
  retrieval, cited Claims, and support checking.

