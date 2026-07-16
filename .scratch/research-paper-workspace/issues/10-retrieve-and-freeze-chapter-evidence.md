# 10 - Retrieve and Freeze Chapter Evidence

**What to build:** A researcher can start real body generation from an approved
Report Outline whose section queries are already versioned; the service
automatically retrieves and freezes each Chapter Evidence Bundle and its
Evidence Coverage without a separate user-facing evidence-curation stage.

**Blocked by:** 09 - Generate, Edit, and Approve an Evidence-Driven Outline.

**Status:** ready-for-agent

- [ ] Starting a Report Operation Attempt retrieves each approved chapter's
  versioned section queries from all ready workspace papers, records query
  attribution, provenance, and evidence-gap state, and creates a bounded
  Chapter Evidence Bundle.
- [ ] The automatic bundles derive Evidence Coverage and are frozen with the
  Attempt. The browser exposes the owning outline query and truthful operation
  state, but does not expose manual Chunk removal, addition, or a separate
  evidence-curation screen.
- [ ] Persistence, API, accepted workspace UI, controlled retrieval tests, and
  a documented provider-backed retrieval acceptance run demonstrate that later
  paper readiness or outline-query edits cannot silently alter a frozen Attempt.
