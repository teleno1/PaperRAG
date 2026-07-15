# 14 - Review Direct Edits and AI Rewrites

**What to build:** A researcher in writing edit mode can resolve citations
after a direct Claim edit and use an AI Rewrite Proposal that is support-checked
against its current sources before it can be applied.

**Blocked by:** 13 - Inspect Claim Evidence and Open the Original PDF.

**Status:** ready-for-agent

- [ ] A substantive direct edit makes its Claim Citation pending review, while
  presentation-only edits preserve state; the browser exposes keep, remove, and
  workspace-scoped refresh with persisted Citation Revision history.
- [ ] The edit-only AI assistant accepts a selected Claim or passage and user
  instruction, returns a non-destructive proposal, and support-checks every
  changed factual Claim against its current Source Chunks before application.
- [ ] A supported proposal may be explicitly applied as verified; a partial or
  unsupported proposal shows its validation reason and cannot automatically
  overwrite the Report Draft, leaving reject, pending-review, or refresh paths.
- [ ] Tests and a documented real-provider manual acceptance run cover direct
  edits, proposal validation, user application, source isolation, no-support
  recovery, and preservation of original Claim and citation history.

