# Workspace stability and discovery resilience

Status: Accepted

Date: 2026-07-13

## Context

The first browser workspace slices exposed durable paper selection, discovery,
and outline editing, but a user could not comfortably inspect long lists on a
desktop viewport. Candidate search results also had no reversible rejection
state, outline history was not visible, and OpenAlex quota responses or
unstable public PDF locations made discovery look unavailable even when a
recoverable next action existed.

## Decision

- Keep the three desktop workspace panels as independent scroll containers with
  stable scrollbar gutters and sticky headings. At mobile widths the panels
  return to ordinary document flow and page scrolling.
- Persist `papers.dismissed_at` as a workspace-scoped, reversible visibility
  flag. Dismissal never deletes a paper, document version, or provenance record;
  selecting a paper clears the flag.
- Persist all ordered public PDF locations from discovery while retaining the
  first URL as the compatibility `pdf_url`. Import attempts each location in
  order and accepts content only after a `%PDF-` signature check.
- Keep OpenAlex credentials in `OPENALEX_API_KEY` only. The provider uses
  `per_page`, bounded request spacing, in-process cache and duplicate-request
  coalescing. A 429 is returned with reset metadata and a manual arXiv switch;
  results are never silently mixed across providers.
- Treat outline restoration as a copy operation: a read-only historical or
  approved revision is copied into a new draft revision with a new immutable
  ID and revision number.

## Consequences

Existing SQLite workspaces migrate on startup before the dismissal index is
created. The browser can offer clear recovery actions without weakening the
product boundary that only ready Selected Papers are evidence. OpenAlex quota
state is process-local and therefore intentionally not a cross-process rate
limiter; the first product remains a single-user, single-process deployment.
