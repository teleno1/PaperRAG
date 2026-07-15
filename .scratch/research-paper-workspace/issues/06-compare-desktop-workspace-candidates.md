# 06 - Compare Desktop Workspace Candidates

**Type:** prototype

**What to build:** A Workspace Owner can use three high-fidelity, desktop-only
Interaction Architecture Candidates over the same controlled research scenario
and complete the normal Research Workspace journey in each, so that information
architecture is compared before production browser work resumes.

**Blocked by:** None - can start immediately. Tickets 01 through 05A establish
the real product behaviour that the prototype represents.

**Status:** complete

**Claimed by:** Codex (2026-07-15)

- [x] A standalone controlled-fixture prototype presents materially different
  flow-driven, report-driven, and evidence-driven candidates with one shared
  research-writing visual baseline. The first candidate implements the proposed
  five Workflow Stages: import, paper reading, outline, evidence curation, and
  writing.
- [x] Every candidate lets the owner operate the complete normal journey from
  Workspace setup through Markdown export, using believable local research
  content without real APIs, PDFs, persistence, credentials, or domain-logic
  duplication.
- [x] Prototype Comparison Mode switches the same scenario among candidates and
  records structured feedback for task clarity, next-action discoverability,
  information load, control discoverability, evidence-checking ease, and free
  notes.
- [x] The fixture exposes faithful Workspace Operation states and an
  owner-visible scenario switcher for review, but no candidate is represented
  as a production or real-provider acceptance result.

## Prototype review entry point

Run `npm.cmd run dev:prototype` from `frontend/`, then open
`http://localhost:5173/prototype.html?variant=flow`.

The bottom switcher (or left/right arrow keys outside input fields) changes
between the three candidates. The review switcher exposes the normal,
partial-readiness, failure/retry, evidence-gap, multi-source, and
citation-review states. Feedback is intentionally held only in memory; the
Workspace Owner's comparison decision belongs in this ticket before it can be
checked off and ticket 07 can begin.

**Verification:** `npm.cmd run build:prototype` passed on 2026-07-15.

## Owner decision (2026-07-15)

The Workspace Owner selected the flow-driven desktop direction after iterative
review. The accepted direction keeps the product title and left-side stage
navigation fixed, gives the central task surface and Task Detail Pane their own
scrolling regions, and uses stage-specific right-side information rather than
one permanent paper-card area.

The selected prototype direction is:

- **Literature import:** search candidates in the centre; use right-side tabs
  for ready papers and importing/failed records, including batch management.
- **Paper reading:** select a ready paper from the right side and read its
  original-PDF fixture in the centre.
- **Report outline:** group sections under a collapsible chapter heading;
  edit section names and their retrieval queries; version both together.
- **Report writing:** make citations inspectable from the continuous report
  text; show provenance, excerpt, verification status, and the reading jump in
  the right side; regenerate at chapter level with written instructions.

At the Owner's direction, the prototype does not expose a separate evidence-
curation stage. Retrieval queries remain first-class editable outline content.
This is a prototype decision that deliberately supersedes the older
evidence-curation presentation in the current product specification; its
domain and delivery documentation will be reconciled once ticket 07's complete
Interaction Contract is accepted.
