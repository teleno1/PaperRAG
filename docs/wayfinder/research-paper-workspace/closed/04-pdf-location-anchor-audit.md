---
type: research
status: closed
claimed_by: null
blocked_by: []
resolved: 2026-07-11
---

# Audit Stable PDF Source-Location Anchors

## Question

Can the existing PDF parsing and chunking path retain stable enough page,
section, and excerpt anchors for a user to inspect the evidence behind a Claim
Citation? If not, what smallest compatible extension is required?

Audit the current MinerU compatibility path, normalized parser output, chunk
metadata, vector metadata, and citation registry. Distinguish required
user-facing anchors from nice-to-have PDF viewer highlights.

## Audit Findings

### What is already available

- `MinerUParser._parse_units` reads the MinerU `content_list_v2.json` page by
  page.  Each `ParsedDocumentUnit` retains the one-based `page_number`, the
  most recently parsed title as `section`, and the extracted block text.  Its
  `ParsedDocument` also retains the original PDF `source_path` and identifies
  MinerU as the parser.
- `DocumentChunk` already has a stable-for-one-index-build `chunk_id`, a
  document identifier, source path/type, section, content, and an extensible
  metadata dictionary.  FAISS persists arbitrary JSON metadata alongside each
  vector, so no vector-store schema change is inherently required.
- Retrieval already returns the paper identity, `chunk_id`, section, title,
  and chunk content.  The review flow maps its ephemeral `source_id` values
  back to `chunk_id` and `paper_id`, so the existing citation guard has a
  useful identity chain on which to build.

### Where the location chain breaks

- `ChunkBuilder.build_chunks_from_parsed_document` converts parsed units to
  only `text` and `section`.  It drops `page_number` and unit/block metadata
  before it merges, splits, or overlaps sentences.  The older
  `build_chunks(content_list_v2.json)` path separately re-parses the manifest
  and never assigns page numbers at all.  Consequently a chunk cannot say
  which page or page range supplied its text.
- The legacy `Chunk` value carries no provenance metadata.  `IndexBuilder`
  calls `chunk_to_document_chunk`, but emits only content, section,
  bibliographic fields, source path/type, and generated ordinal `chunk_id`.
  It therefore cannot carry a page range, clean source excerpt, parser/version,
  or source-document fingerprint into FAISS metadata.
- `FaissRecallService` and `RetrievedSource` reconstruct only those emitted
  fields.  The generic query/report API follows the same shape, so a UI cannot
  request a user-facing location from a retrieved source today.
- `SourceRegistry` persists source-to-chunk and source-to-paper mappings plus
  paper bibliographic metadata.  `CitationRegistry` reduces this further to
  paper-level references.  They do not retain the source path, page/section
  anchor, or an evidence snapshot for a cited source.  Existing review export
  renders paper-number citations only; it cannot power a claim Task Detail Pane.
- Current ordinal chunk IDs (for example `paper__chunk_0002`) are suitable as
  an index-build identity, but are not immutable across a changed parser,
  chunking configuration, reordered input, or re-upload.  A report must keep
  the particular paper artifact/version and anchor snapshot that it used,
  rather than resolving an old citation against whichever index happens to be
  current.
- The current chunk content is decorated with `[Title: ...]` and `[Section:
  ...]` before the original text.  It is adequate retrieval input but is not a
  clean source excerpt to show verbatim in an evidence panel.

### Implication for the first-version interaction

The foundation is sufficient to implement a trustworthy side-panel trace, but
not yet to claim page-level traceability.  For every cited source, the panel
must be able to show the selected paper's title, a retained source reference,
the section when known, a page number or inclusive page range when known, and
the exact clean excerpt that formed the chunk.  A missing page is acceptable
for a parser/source type that cannot supply one, provided the UI says so rather
than inventing it.

Pixel coordinates, bounding boxes, PDF.js navigation, and highlighted regions
in a full PDF reader are **not** required for this product version.  MinerU's
current compatibility manifest is also not being audited as a reliable
coordinate source here; page/section/excerpt anchors are the deliberately
smaller contract.

## Recommended Resolution

Adopt a serializable, versioned `SourceAnchor` value at the chunk boundary and
propagate it unchanged through indexing, retrieval, and persisted claim
citations.  The smallest compatible shape is:

```text
SourceAnchor
  document_version_id        # upload/import artifact version, not just paper_id
  source_path or source_url  # original authorized PDF/reference
  page_start?: int           # one-based, inclusive
  page_end?: int             # one-based, inclusive; same as start for one page
  section?: str              # nearest parsed heading; no hierarchy promise
  excerpt: str               # clean, un-decorated chunk text shown to the user
  parser: str                # e.g. "mineru"
  parser_version?: str
  chunking_version?: str
```

`document_version_id`, parser/chunking versions, and the source anchor snapshot
make an anchor stable for the report version that cited it.  Reprocessing a
paper creates a new document version; it must not silently rewrite the anchor
of an existing report citation.

Implement this as a compatible extension, not a rewrite:

1. Preserve page and block provenance while `ChunkBuilder` merges/splits
   `ParsedDocumentUnit` values.  Each resulting chunk receives the minimum and
   maximum page covered by its contributing units, its current nearest-heading
   section, and a clean excerpt before retrieval-only title/section decoration.
   The old manifest path should use the same provenance-aware unit/chunk
   construction (or be adapted to it) so `content_list_v2.json` remains a
   supported compatibility input.
2. Add optional chunk provenance metadata (or an explicit `SourceAnchor`) to
   the legacy `Chunk` adapter, copy it into `DocumentChunk.metadata`, and emit
   it in FAISS metadata.  Keep all existing metadata keys and chunk IDs so
   generic RAG callers remain compatible.
3. Add the optional anchor to `RetrievedSource` and API response models, and
   retain it in the retrieval/review source registry.  A future workspace
   `ClaimCitation` stores the resolved anchor snapshot alongside its chunk ID;
   it must not depend solely on a temporary review-run `SRC-*` identifier.
4. Add focused tests with a multi-page MinerU fixture, including a chunk that
   spans a page boundary, to prove page range/section/excerpt survival through
   parse -> chunk -> index metadata -> retrieval -> citation registry.  Add a
   reprocess/version test proving an old citation still resolves to its saved
   evidence snapshot.

The claim Task Detail Pane should show `p. N`, `pp. N-M`, section, and excerpt
when each is present; it should otherwise show the original source reference
and an explicit "page unavailable from this parse" state.  Defer viewer
deep-links, bounding boxes, and in-document highlighting to a later ticket
only if user research shows that page/section/excerpt inspection is
insufficient.
