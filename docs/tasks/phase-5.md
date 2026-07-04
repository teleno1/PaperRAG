# Phase 5 Tasks: Deployment and Portfolio Packaging

## T5-01: Add deployment files

Status: todo
Phase: Phase 5
Priority: high

Goal:
Make the project runnable in a fresh environment.

Allowed Changes:
- Add Dockerfile.
- Add docker-compose file.
- Add `.env.example`.

Acceptance:
- Docker setup documents required environment variables.
- Generated data remains mounted/ignored appropriately.
- Tests still pass locally.

Verification:
- `python -m pytest -q`
- `docker compose config`

Notes:
- Do not require real API keys for container config validation.

## T5-02: Complete health/state and run visibility

Status: todo
Phase: Phase 5
Priority: medium

Goal:
Expose enough runtime status for deployment and debugging.

Allowed Changes:
- Extend `/health` and `/state` if needed.
- Add run/eval status inspection if needed.
- Add tests for status responses.

Acceptance:
- API can report service health.
- API or CLI can report index and eval/run artifact state.
- Existing routes remain compatible.

Verification:
- `python -m pytest -q`
- `python -m app.cli.main health`

Notes:
- Avoid adding persistent services unless necessary.

## T5-03: Update README for portfolio presentation

Status: todo
Phase: Phase 5
Priority: high

Goal:
Make the finished project understandable to recruiters and interviewers.

Allowed Changes:
- Add quickstart.
- Add architecture overview.
- Add eval results table.
- Add one success trace and one failure analysis.
- Add resume-oriented project summary.

Acceptance:
- README distinguishes current capabilities from target roadmap only if any
  tasks remain unfinished.
- README shows commands for test, ingest, query/report, eval, and API startup.
- README includes the final evaluation metrics.

Verification:
- `python -m pytest -q`

Notes:
- Do not exaggerate unfinished capabilities.

## T5-04: Final project acceptance

Status: todo
Phase: Phase 5
Priority: high

Goal:
Verify the project meets the Definition of Done.

Allowed Changes:
- Fix small integration/documentation gaps found during final acceptance.
- Update final docs and README.

Acceptance:
- Fresh environment can follow README to run tests and minimal demo.
- Eval dataset has at least 30 questions.
- Metrics satisfy `Recall@5 >= 80%`, `citation_hit_rate >= 90%`,
  `unknown_citation_count = 0`, and format compliance `>= 90%`.
- Strategy comparison exists for chunking, retrieval, and rerank.
- Project summary is ready to place in the resume.

Verification:
- `python -m pytest -q`
- README quickstart commands
- Eval command against the final dataset

Notes:
- This is not a feature task. It is the acceptance pass before resume writing
  and RAG JD投递.

