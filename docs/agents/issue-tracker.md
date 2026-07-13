# Issue Tracker: Local Markdown Fallback

GitHub remains the repository host, but its connected integration cannot create
issues here. Do not treat GitHub Issues or `gh issue create` as the active
tracker until write access is restored.

## Canonical local records

- The active planning map is
  [`docs/wayfinder/research-paper-workspace.md`](../wayfinder/research-paper-workspace.md).
- Open or resolved Wayfinder decision tickets live beside the map; resolved
  tickets move to `docs/wayfinder/research-paper-workspace/closed/`.
- Delivery tickets live in `.scratch/research-paper-workspace/issues/`. Their
  `Status` and `Active blockers` fields describe implementation readiness.

## Local workflow

- Claim a Wayfinder ticket by setting its `claimed_by` field before working.
- Resolve a decision in the ticket, update `CONTEXT.md` and the product spec
  when required, move the ticket to `closed/`, and update the map.
- For implementation, update the delivery ticket locally, run its verification,
  and create the required checkpoint commit.
- When GitHub issue write access returns, migrate only the still-active local
  records deliberately; do not recreate the closed decision history blindly.
