# 05D — Publish a Complete Evidence-Driven Literature Report

**What to build:** A researcher can turn completed body-chapter results into a
single, editable Literature Report only when the report is complete: a derived
and verified conclusion, independently grounded outlook, uncited derived
abstract, and deterministic references are assembled without rewriting verified
body Claims.

**Blocked by:** 05C — Generate Verified Body Chapters.

**Status:** ready-for-agent

**Deferred UX constraint:** This ticket delivers only the smallest usable
browser interface needed to complete its user task. Except for accessibility or
legibility fixes, it must not redesign the workspace information architecture,
global navigation, three-panel layout, visual system, or shared component
styling. Keep feature behaviour in independent components and separate from
API, persistence, and domain state so a later accepted prototype can change
presentation safely; browser acceptance must use semantic selectors rather than
CSS structure.

- [ ] Conclusion-and-outlook waits for body chapters. Conclusion entries name
  one or more existing Claim IDs, inherit and pass a support check against their
  Source Chunks; outlook Claims use their own retrieved and validated evidence.
  The abstract waits for the completed report, has no retrieval or visible
  citations, and retains internal derived-Claim links only.
- [ ] Final synthesis returns strict JSON and never rewrites, reorders, or
  polishes verified body Claims. It gets one repair attempt on invalid JSON;
  failure preserves the Attempt and prior draft rather than publishing partial
  content.
- [ ] The service atomically publishes a new editable Report Draft only after
  all required chapters reach cited or evidence-gap terminal states. Retry runs
  failed work and downstream dependencies only; user-requested regeneration
  creates a new Attempt.
- [ ] References are rendered without retrieval or model calls from the
  Attempt's Evidence Coverage, include every ready covered paper as cited or
  consulted-but-uncited, and use first-appearance clickable `[n]` citations,
  GB/T 7714 ordering for Chinese, and truthful missing metadata handling.
- [ ] Persistence, API, minimal browser report view, controlled tests, and a
  documented real-provider manual acceptance run cover full atomic publication,
  inherited conclusion provenance, abstract non-citation, outlook support, and
  references.

