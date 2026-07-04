# Phase 1 Tasks: Document-Centric Domain Models

## T1-01: Add document-centric domain models

Status: done
Phase: Phase 1
Priority: high

Goal:
Introduce general RAG concepts without breaking the paper-specific pipeline.

Allowed Changes:
- Add `DocumentMetadata`, `DocumentChunk`, `Source`, and related model tests.
- Keep existing `PaperMetadata` and `Chunk` code working.

Acceptance:
- New models include `document_id`, `source_path`, `source_type`, `section`,
  `chunk_id`, `content`, and optional metadata.
- Unit tests cover model validation and serialization.
- Existing tests pass.

Verification:
- `python -m pytest -q`

Notes:
- Do not rename the whole domain package in this task.
- Completed by adding `Source`, `DocumentMetadata`, and `DocumentChunk` in
  `app/domain/models/document.py`, exporting them from
  `app/domain/models/__init__.py`, and covering validation plus serialization
  with `tests/test_document_models.py`.
- Kept existing `PaperMetadata` and `Chunk` untouched so the paper-specific
  pipeline remains compatible at this phase.

## T1-02: Add compatibility adapters for old paper models

Status: todo
Phase: Phase 1
Priority: high

Goal:
Map existing `PaperMetadata` and `Chunk` outputs into document-centric models.

Allowed Changes:
- Add adapter functions or classes.
- Add tests using existing paper-style fixtures.

Acceptance:
- Existing chunk metadata can be converted to document-style metadata.
- Compatibility fields such as `paper_id` are preserved where old code needs
  them.
- Existing tests pass.

Verification:
- `python -m pytest -q`

Notes:
- Prefer adapters over broad renames.

## T1-03: Add document metadata to vector index records

Status: todo
Phase: Phase 1
Priority: high

Goal:
Ensure indexed chunks carry general source metadata.

Allowed Changes:
- Update index metadata generation to include `document_id`, `source_path`,
  `source_type`, and `chunk_id`.
- Keep existing `paper_id` compatibility metadata if required by tests.

Acceptance:
- New metadata fields appear in saved metadata records.
- Existing retrieval code still works.
- Tests cover metadata shape.

Verification:
- `python -m pytest -q`

Notes:
- Do not change vector storage backend in this task.
