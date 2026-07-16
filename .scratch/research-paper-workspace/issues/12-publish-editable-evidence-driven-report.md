# 12 - Publish an Editable Evidence-Driven Literature Report

**What to build:** A researcher can receive a single, complete Literature
Report from completed body chapters and use its accepted continuous writing
stage to trace cited sentences, regenerate a chapter with an instruction,
auto-save direct changes, save an immutable version, and later export truthful
complete content.

**Blocked by:** 11 - Generate Verified Body Chapters.

**Status:** ready-for-agent

- [ ] Conclusion-and-outlook waits for body chapters, verifies inherited
  conclusion sources and independently grounded outlook Claims; abstract waits
  for the completed report and derives only from existing Claims; references are
  deterministic from curated Evidence Coverage without retrieval or model calls.
- [ ] Final synthesis never rewrites, reorders, or polishes verified body
  Claims. Invalid JSON gets one repair; any final failure preserves the Attempt
  and prior draft rather than publishing partial content.
- [ ] A new editable Report Draft is atomically published only after every
  required chapter reaches cited or evidence-gap terminal state. Writing uses
  the accepted continuous-text surface, exposes chapter-level regeneration,
  displays auto-save state for direct changes, and creates a Report Revision
  only on explicit save; it does not add a preview/edit mode switch.
- [ ] Persistence, API, accepted writing UI, controlled tests, and a documented
  real-provider manual acceptance run cover atomic publication, provenance,
  editing persistence, and truthful deterministic references.
