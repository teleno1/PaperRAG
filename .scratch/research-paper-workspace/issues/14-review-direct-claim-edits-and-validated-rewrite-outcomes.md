# 14 - Review Direct Claim Edits and Validated Rewrite Outcomes

**What to build:** A researcher can resolve citations after a direct Claim edit
in the accepted continuous writing surface. If a validated AI Rewrite Proposal
enters citation review, its support-checked outcome is preserved without adding
a dedicated assistant control that is absent from the Interaction Contract.

**Blocked by:** 13 - Inspect Claim Evidence and Open the Original PDF.

**Status:** ready-for-agent

- [ ] A substantive direct edit makes its Claim Citation pending review, while
  presentation-only edits preserve state; the browser exposes keep, remove, and
  workspace-scoped refresh with persisted Citation Revision history.
- [ ] A support-checked AI Rewrite Proposal, when supplied to the review flow,
  remains non-destructive until explicitly applied. Every changed factual Claim
  is checked against its current Source Chunks; a partial or unsupported result
  shows its validation reason and cannot automatically overwrite the Report
  Draft, leaving reject, pending-review, or refresh paths.
- [ ] Tests and a documented real-provider manual acceptance run cover direct
  edits, proposal validation, user application, source isolation, no-support
  recovery, and preservation of original Claim and citation history.
