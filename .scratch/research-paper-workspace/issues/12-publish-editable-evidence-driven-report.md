# 12 - Publish an Editable Evidence-Driven Literature Report

**What to build:** A researcher can receive a single, complete Literature
Report from completed body chapters and use its accepted writing stage to
preview, enter editing mode, auto-save a Report Draft, save an immutable
version, and export only truthful complete content later.

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
  required chapter reaches cited or evidence-gap terminal state. Writing
  defaults to preview, enters edit mode explicitly, displays auto-save state,
  and creates a Report Revision only on explicit save.
- [ ] Persistence, API, accepted writing UI, controlled tests, and a documented
  real-provider manual acceptance run cover atomic publication, provenance,
  editing persistence, and truthful deterministic references.

