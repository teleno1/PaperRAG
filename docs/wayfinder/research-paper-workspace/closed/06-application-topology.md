---
type: grilling
status: closed
claimed_by: Codex
blocked_by: []
resolved: 2026-07-12
---

# Choose the Single-User Application Topology

## Question

What frontend, API, persistence, background-work, and deployment composition
best fits the validated first-version workflow while preserving the useful
Python/FastAPI/RAG components already in the repository?

The decision must define the boundary between the web application and existing
use cases, local persistent storage, long-running import/generation visibility,
and the smallest deployable package.

## Resolution

The first-version product is one locally deployed application. Its browser
surface is a React + TypeScript single-page application. During development the
frontend may run separately for hot reload; the production FastAPI application
serves the compiled static assets and the same-origin API. There is no SSR,
Next.js application, second runtime service, or gateway.

The web application calls versioned workspace-oriented JSON endpoints under
`/api/workspaces/...` and operation endpoints under `/api/operations/{id}`.
They expose product state, permitted actions, and evidence data, never local
paths, FAISS internals, or provider implementation details. Existing generic
routes and CLI commands remain compatibility surfaces and are not dependencies
of the new browser application.

SQLite is the authoritative store for workspace metadata, versions, Claims,
citations, and Workspace Operations. Managed local files hold PDFs, parsed
artifacts, and workspace/version-scoped FAISS indexes. Persistence is accessed
through Python repository adapters using `sqlite3`; no ORM, database server, or
cloud service is introduced. All durable data lives below one configurable
deployment data directory. First-version backup and migration are documented
as stopping the service and copying that directory; there is no automatic,
cloud, or browser-mediated backup feature.

Long-running import, parse, index, outline/report generation, and citation
refresh operations run through an in-process durable executor. Submitting work
returns a Workspace Operation ID; status, phase, safe error category, retry
action, timestamps, progress counts, and current paper/section are persisted
in SQLite. The browser polls while an operation is active. A restart marks
running work `interrupted` and retryable; partial streamed output never becomes
report content or evidence. The executor serializes state-changing operations
within a workspace and applies a small global concurrency limit. A queued
operation may be cancelled, while a running operation is allowed to finish or
fail rather than being forcefully interrupted.

The production process is exactly one Uvicorn worker, launched through the
native Python package's `paperrag serve` command (or its equivalent). It serves
the API, static frontend, and in-process executor, defaults to `127.0.0.1`,
and uses a configured local data directory. Docker, Compose, public exposure,
authentication, multi-worker execution, and horizontal replicas are not v1
requirements. Remote exposure is only an explicit deployment choice behind a
trusted reverse proxy; the product itself supplies no access control.

### Acceptance examples

| Scenario | Required result |
| --- | --- |
| Browser creates a workspace or starts import/generation | The API responds with product state or a Workspace Operation ID without blocking on the long-running work. |
| Browser reloads while work is active | It restores the workspace and polls the persisted operation, including phase, progress, and retryable failure information. |
| The service stops during an active operation | On restart, that operation is `interrupted`, never `succeeded`; retry starts a new safe attempt. |
| Two state-changing requests target the same workspace | The second request is queued rather than racing the first; a queued request can be cancelled. |
| Production package starts | One local FastAPI/Uvicorn process serves the compiled frontend and `/api` endpoints from a configurable data directory. |
