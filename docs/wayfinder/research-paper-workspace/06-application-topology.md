---
type: grilling
status: open
claimed_by: null
blocked_by:
  - 01-workspace-provenance-contract
  - 02-evidence-trace-prototype
  - 03-paper-discovery-research
---

# Choose the Single-User Application Topology

## Question

What frontend, API, persistence, background-work, and deployment composition
best fits the validated first-version workflow while preserving the useful
Python/FastAPI/RAG components already in the repository?

The decision must define the boundary between the web application and existing
use cases, local persistent storage, long-running import/generation visibility,
and the smallest deployable package.
