# Outline-query controlled retrieval

Status: Accepted

Date: 2026-07-15

The accepted Workspace Interaction Architecture has no separate user-facing
evidence-curation stage. The Workspace Owner controls body retrieval by editing
and versioning section queries alongside the Report Outline; a Report Operation
Attempt automatically retrieves and freezes its Chapter Evidence Bundles and
derived Evidence Coverage. This deliberately replaces manual per-Chunk
addition/removal and global Evidence Curation Version confirmation: it keeps
the evidence boundary and frozen provenance while removing a workflow the Owner
does not want to manage. ADR 0005 remains the source for bounded retrieval,
support validation, and frozen attempt provenance except where its manual
curation presentation conflicts with this decision.
