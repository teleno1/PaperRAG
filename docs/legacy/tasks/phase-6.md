# Phase 6 Tasks: Deployment and Portfolio Packaging

## T6-01: Add deployment files

Status: todo
Phase: Phase 6
Priority: high

Goal:
Make the project runnable in a fresh environment.

Allowed Changes:
- Add Dockerfile.
- Add docker-compose file.
- Add `.env.example`.

Acceptance:
- Docker setup documents required environment variables.
- Generated data remains mounted or ignored appropriately.
- Tests still pass locally.

Verification:
- `python -m pytest -q`
- `docker compose config`

Notes:
- Do not require real API keys for container config validation.

## T6-02: Complete health/state and run visibility

Status: todo
Phase: Phase 6
Priority: medium

Goal:
Expose enough runtime status for deployment and debugging.

Allowed Changes:
- Extend `/health` and `/state` if needed.
- Add run or eval status inspection if needed.
- Add tests for status responses.

Acceptance:
- API can report service health.
- API or CLI can report index and eval or run artifact state.
- Existing routes remain compatible.

Verification:
- `python -m pytest -q`
- `python -m app.cli.main health`

Notes:
- Keep this task focused on deployment-time observability rather than
  evaluation-definition changes.

## T6-03: Update README for portfolio presentation

Status: todo
Phase: Phase 6
Priority: high

Goal:
Make the finished project understandable to recruiters and interviewers.

Allowed Changes:
- Add quickstart.
- Add architecture overview.
- Add final eval results table.
- Add one success trace and one failure analysis.
- Add resume-oriented project summary.

Acceptance:
- README distinguishes current capabilities from target roadmap only if any
  tasks remain unfinished.
- README shows commands for test, ingest, query or report, eval, and API
  startup.
- README includes the final evaluation metrics.

Verification:
- `python -m pytest -q`

Notes:
- README packaging in this phase should rely on the already completed final
  evaluation outputs from Phase 5.

## T6-04: Final deployment and portfolio acceptance

Status: todo
Phase: Phase 6
Priority: high

Goal:
Verify the deployment, demo, and portfolio packaging are complete and
accurately presented.

Allowed Changes:
- Fix small deployment, packaging, or documentation gaps found during final
  acceptance.
- Update final docs and README.

Acceptance:
- A fresh environment can follow README to run tests and the minimal demo.
- Docker Compose starts successfully.
- `/health` responds.
- README accurately describes current capabilities, evaluation results, and
  limits.

Verification:
- `python -m pytest -q`
- `docker compose up --build`
- README quickstart commands

Notes:
- This task does not own the final evaluation thresholds; those are completed
  in Phase 5.
