# 10 - Curate and Confirm Chapter Evidence

**What to build:** A researcher can use an approved Report Outline to inspect
each chapter's retrieval queries and candidates, curate evidence from every
ready Selected Paper, and explicitly confirm one Evidence Curation Version for
real body generation.

**Blocked by:** 09 - Generate, Edit, and Approve an Evidence-Driven Outline.

**Status:** ready-for-agent

- [ ] The evidence-retrieval stage shows each chapter's section queries and
  vector candidates from all ready workspace papers, with retained retrieval
  attribution, provenance, and evidence-gap state.
- [ ] The researcher can remove a candidate and manually search every ready
  Selected Paper's Chunks to add an eligible Chunk; changes persist as a new
  chapter-aware Evidence Curation Version rather than an unrecorded override.
- [ ] One explicit global confirmation requires every body chapter to be curated
  or deliberately marked as an evidence gap, derives Evidence Coverage from the
  actually retained/added Chunks, and freezes that version for a later Report
  Operation Attempt.
- [ ] Persistence, API, accepted workspace UI, controlled retrieval tests, and
  a documented provider-backed retrieval acceptance run demonstrate that later
  paper readiness or curation edits cannot silently alter a confirmed version.

