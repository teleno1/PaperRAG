# 08 - Connect Preparation and Reading to the Accepted Workspace

**What to build:** A researcher can use the accepted desktop workspace to
create a real Workspace, upload or discover Selected Papers, recover from
preparation failures, and read any ready paper in its authorised original PDF.

**Blocked by:** 07 - Accept the Complete Workspace Interaction Prototype.

**Status:** ready-for-agent

- [ ] Production browser state is supplied through the accepted Workspace View
  State contract and implements the accepted import and paper-reading stages;
  all Workflow Stages remain visible, while unavailable stages explain their
  prerequisite and offer the next permitted action.
- [ ] The import stage provides upload and open-paper search, an operation list
  with truthful progress/failure/retry, and a distinct ready-paper collection;
  it preserves Candidate Paper and Selected Paper boundaries.
- [ ] The paper-reading stage renders the active authorised original PDF rather
  than reconstructed Chunk text, lets the user switch ready papers, and reports
  unavailable historical PDFs truthfully without a synthetic reader.
- [ ] API, persistence, browser acceptance, and regression tests cover the
  real preparation/read path and verify that the prototype fixture is not used
  in production.

