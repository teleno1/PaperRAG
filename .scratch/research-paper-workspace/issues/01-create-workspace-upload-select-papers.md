# 01 — Create a Research Workspace and Select Uploaded Papers

**What to build:** A researcher can create a Research Workspace, select its
Chinese or English Report Language, upload an authorised PDF, see its processing
state, and explicitly make it a Selected Paper. Only a Selected Paper is usable
as workspace evidence; an upload that fails processing gives the user a clear,
recoverable status.

**Blocked by:** Wayfinder decisions: Model the Research Workspace and
provenance contract; Prototype the report editor and evidence-trace interaction;
Audit stable PDF source-location anchors; Choose the single-user application
topology.

**Status:** ready-for-agent

- [ ] A user can create and revisit a single-user workspace with topic and
  Report Language.
- [ ] A user can upload an authorised PDF, see readiness or a recoverable
  processing failure, and select or remove the resulting Research Paper.
- [ ] Unselected or unsuccessfully processed papers cannot be used as evidence
  by downstream workspace operations.
- [ ] The workflow is available through the chosen browser/API surface and is
  covered with fake-based external-service tests.
