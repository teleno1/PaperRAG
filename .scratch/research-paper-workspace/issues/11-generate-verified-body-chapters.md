# 11 - Generate Verified Body Chapters

**What to build:** A researcher can start a Report Operation Attempt from an
approved Outline Revision and its automatically frozen Chapter Evidence Bundles
and observe real, recoverable body-chapter
generation where every factual Claim is grounded and support-checked before
final report assembly.

**Blocked by:** 10 - Retrieve and Freeze Chapter Evidence.

**Status:** ready-for-agent

- [ ] Up to two independent body chapters run concurrently from the frozen
  automatic Chapter Evidence Bundles. Within a chapter, generation, source-ID
  validation, support checking, and at most one claim regeneration run serially;
  remaining failures are explicit evidence gaps.
- [ ] The accepted workspace shows queued/running/validating/failed chapter
  state, safe errors, evidence gaps, and retry actions. An Attempt persists
  frozen inputs, ChapterRuns, normalized bundles, Claim candidates, verdicts,
  and retries, but publishes no provisional Report Draft.
- [ ] Retry retains successful chapter work and reruns failed chapters and their
  dependencies only. Empty automatic bundles complete as deliberate all-gap
  results without a body-model call.
- [ ] Controlled tests and a documented real-provider manual acceptance run
  demonstrate actual body generation, cited Claims, support checking, and
  recovery through the accepted workspace interface.
