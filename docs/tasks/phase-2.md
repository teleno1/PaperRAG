# Phase 2 Tasks: General Ingestion

## T2-01: Define a general parser interface

Status: done
Phase: Phase 2
Priority: high

Goal:
Create a unified interface for document parsers.

Allowed Changes:
- Add parser protocol/interface and normalized document unit models.
- Add tests with fake parser implementations.

Acceptance:
- Parser interface can represent `PDF`, `TXT`, and `Markdown` sources.
- Normalized units include content, section/page when available, and metadata.
- Existing tests pass.

Verification:
- `python -m pytest -q`

Notes:
- Do not implement all parsers in this task unless the user explicitly expands
  scope.
- Added `ParsedDocument` and `ParsedDocumentUnit` as the normalized parser
  boundary before chunking.
- Added `DocumentParser` protocol and `ParserRegistry` with fake-parser tests
  covering extension-based selection and invalid payload handling.
- Review suggestion recorded: add constructor validation tests for
  `ParserRegistry` when Phase 2 parser implementations expand.

## T2-02: Implement TXT and Markdown parsers

Status: todo
Phase: Phase 2
Priority: high

Goal:
Support non-PDF ingestion without external APIs.

Allowed Changes:
- Add TXT parser.
- Add Markdown parser.
- Add small fixtures for parser tests.

Acceptance:
- TXT and Markdown files become normalized document units.
- Parsing does not require API keys.
- Tests cover headings/sections for Markdown and plain text fallback for TXT.

Verification:
- `python -m pytest -q`

Notes:
- Keep parser logic simple and deterministic.

## T2-03: Wrap MinerU as the PDF parser

Status: todo
Phase: Phase 2
Priority: medium

Goal:
Keep existing PDF support while aligning it with the parser interface.

Allowed Changes:
- Add MinerU parser adapter.
- Reuse existing MinerU client.
- Add tests with fake MinerU output.

Acceptance:
- PDF parsing outputs normalized document units.
- Non-PDF flows do not require `MINERU_API_KEY`.
- Existing PDF-related behavior remains compatible.

Verification:
- `python -m pytest -q`
- `python -m app.cli.main health`

Notes:
- Do not remove MinerU support.

## T2-04: Index a tiny TXT/Markdown sample corpus

Status: todo
Phase: Phase 2
Priority: high

Goal:
Prove general ingestion can build an index without PDF parsing.

Allowed Changes:
- Add tiny sample files under an approved sample-data path.
- Add or update CLI flow if needed for indexing sample documents.
- Add tests for sample indexing with fake embeddings.

Acceptance:
- A tiny TXT/Markdown sample corpus can be parsed, chunked, embedded with fakes,
  and indexed in tests.
- No external API calls are required in tests.
- Existing tests pass.

Verification:
- `python -m pytest -q`
- `python -m app.cli.main health`

Notes:
- Do not commit generated FAISS indexes.
