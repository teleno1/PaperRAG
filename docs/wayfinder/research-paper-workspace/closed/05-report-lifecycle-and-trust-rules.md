---
type: grilling
status: closed
claimed_by: Codex
blocked_by: []
resolved: 2026-07-12
superseded_by: docs/adr/0005-evidence-driven-section-report-generation.md
---

# Specify the Report Lifecycle and Trust Rules

## Question

Given the workspace and evidence-trace model, what precise lifecycle governs
outline generation, draft generation, user edits, citation review, citation
refresh, regeneration, source removal, and recovery from unavailable evidence?

The decision must produce user-visible states and acceptance examples for full,
partial, and unsupported report claims without leaking offline evaluation labels
into runtime behavior.

## Resolution

Generation uses only active, ready Selected Papers in the same Research
Workspace. This historical decision's ready-subset selection rule is superseded:
all ready papers are eligible for planning and retrieval, and the confirmed
Evidence Curation Version determines the body evidence and derived Evidence
Coverage. Papers that are not ready remain excluded with their reason, and a
paper that becomes ready later never silently changes a report. No report body
may be generated when no ready evidence exists. A requested section with
insufficient support receives an explicit evidence-gap note rather than an
uncited factual conclusion.

An Outline Revision is `draft` until the user explicitly approves it. Only an
approved outline can generate a report. Editing it returns the new current
outline to `draft` and makes earlier reports out of sync, without invalidating
their historical claims or citations. Regeneration creates a separate,
persisted report draft and never overwrites the current report; the user must
select it to make it current. Report drafts auto-save across browser refreshes,
while an immutable Report Revision is created only by an explicit save.

The Claim's normalized visible text is the trust boundary. A direct change makes
every attached current Claim Citation `pending_review`; style, layout, and
citation-marker-only edits preserve its state. A user-requested AI Rewrite
Proposal may be applied as verified only after it passes the same source-bounded
support check. The user may remove a citation, confirm it (which changes it to
`user_confirmed`, never `verified`), or refresh it. Refresh searches only
active, ready Selected Papers in the same workspace,
records its Evidence Coverage, and creates a successor Citation Revision only
when it finds valid support for the displayed Claim. A failed refresh leaves
the old evidence revision inspectable and the current citation `pending_review`
with an explicit no-support result.

Removing a paper, or replacing a cited active Document Version, makes any
current Claim Citation containing one of its chunks `evidence_unavailable`,
even if that citation also contains other active chunks. The historical source
anchor remains inspectable. No automatic pruning, remapping, or refresh is
permitted. Only a successful user-requested refresh restores `verified`.

A failed outline generation, report generation, regeneration, or citation
refresh records its phase and input snapshot for retry, but never overwrites
the current outline, report, or citation. Incomplete streamed text is not
report content and produces no Claims or citations.

Every report shows a Report Trust Summary: Evidence Coverage, counts by
Citation Review State, and evidence-gap notes. It is `needs attention` when it
has a gap, pending-review citation, or evidence-unavailable citation;
otherwise it is ready to export. Markdown export is permitted in either state
and carries the coverage/attention notice and non-verified citation labels, so
unresolved trust information is not hidden. These are product-facing states,
not the legacy evaluation labels.

### Acceptance examples

| Scenario | Required visible result |
| --- | --- |
| All selected papers are ready and retrieved sources support the generated claims | The attempt records full selected Evidence Coverage; citations are verified and the report is ready to export. |
| One selected paper is parsing or failed | It is unavailable for body evidence and named with its reason. Later readiness does not alter an already confirmed Evidence Curation Version automatically. |
| Ready papers do not support one outline section | Supported sections may generate; the unsupported section shows an evidence-gap note and the report needs attention. |
| User changes Claim text | Its citations become pending review. User confirmation produces user-confirmed; only a successful refresh produces verified. |
| Refresh finds no valid support, or a cited paper/version leaves the active boundary | The old source anchor remains visible; the citation is respectively pending review with no-support, or evidence-unavailable. |
| A generation or refresh fails | The current persisted report and evidence remain unchanged, with a phase-specific retry action. |
