---
type: research
status: closed
claimed_by: null
blocked_by: []
resolved: 2026-07-11
---

# Research Open-Paper Discovery and Import Adapters

## Question

Which open academic indexes and public-PDF discovery paths can support the
first-version Candidate Paper search reliably, with enough metadata,
provenance, rate-limit clarity, and lawful full-text import behavior?

Compare feasible adapters such as OpenAlex and arXiv against the product's
selected-paper and open-PDF boundary. Record a recommendation and failure
behavior for missing, restricted, duplicate, or non-PDF results.

## Research Findings

### OpenAlex

- OpenAlex is the broad discovery index. Its `Works` endpoint supports keyword
  search, filters, sorting, pagination, and work lookups by DOI; a result page
  carries a stable OpenAlex work ID. Use it to create **Candidate Papers**
  only, preserving the provider ID, DOI where present, title, authors,
  publication date/year, abstract when present, venue/location links, OA
  status, and the discovery query/snapshot time. Its documented Works filters
  include `is_oa`, `has_pdf_url`, `has_fulltext`, `is_retracted`, and the
  `best_oa_location` / `primary_location` license, landing-page, and version
  fields. [OpenAlex Works schema](https://developers.openalex.org/api-reference/works),
  [API overview](https://developers.openalex.org/api-reference/introduction)
- A free API key is suitable for a single-user first version: it provides a
  daily $1 allowance, documented as up to 1,000 keyword searches and 100 PDF
  content downloads. The adapter must put the key in deployment configuration,
  never in a repository or client bundle, monitor rate-limit headers, and use
  `per_page` / `select` to avoid needless calls. The provider returns `429`
  when the daily limit is exhausted and documents exponential backoff for `429`
  and transient server errors. [Authentication and pricing](https://developers.openalex.org/api-reference/authentication),
  [error handling](https://developers.openalex.org/api-reference/errors)
- OpenAlex's metadata are CC0, but metadata that says a work is OA or has a
  PDF link is not a promise that the linked host will currently return a PDF,
  nor a blanket redistribution licence for its full text. The API also offers
  a cached-PDF content endpoint at $0.01 per download; it is unnecessary for
  the first version because it adds a paid/provider-hosted full-text path.
  [OpenAlex overview](https://developers.openalex.org/),
  [LLM quick reference](https://developers.openalex.org/guides/llm-quick-reference)

### arXiv

- arXiv is a strong direct-import companion for its own e-prints. Its Atom API
  accepts topic field queries (`ti`, `abs`, `all`, etc.), `id_list`, paging,
  and sort order. Entries provide title, canonical abstract URL/ID, published
  and updated dates, summary, ordered authors, categories/primary category,
  and optional DOI, journal reference, affiliation, and comment. The entry
  documents a related link with `title="pdf"` and `type="application/pdf"`;
  preserve that versioned URL and the canonical abstract URL. [arXiv API user
  manual](https://info.arxiv.org/help/api/user-manual.html), [entry links](https://info.arxiv.org/help/api/user-manual.html#3323-links),
  [article versions](https://info.arxiv.org/help/api/user-manual.html#511-a-note-on-article-versions)
- The legacy API is limited to **one request every three seconds and one
  connection** across machines under the application's control. Cache query
  results, serialize calls, and present a retryable discovery failure rather
  than parallelizing around that limit. Malformed queries are represented as
  Atom error feeds; a valid query can return no entries. [API terms of
  use](https://info.arxiv.org/help/api/tou.html#rate-limits), [API errors](https://info.arxiv.org/help/api/user-manual.html#34-errors)
- arXiv permits retrieving, storing, and using e-print content for personal or
  research purposes, but e-prints remain copyright-protected. It prohibits
  storing **and serving** PDFs unless the rights holder or that version's
  licence permits it; the Atom metadata does not supply a licence field.
  Therefore the product may privately ingest a user-selected arXiv PDF for
  this single-user workspace, retain its source link and version, and must not
  expose cached papers as a general download service or imply that all arXiv
  content is openly licensed. [arXiv API terms](https://info.arxiv.org/help/api/tou.html),
  [arXiv licence guidance](https://info.arxiv.org/help/license/index.html)

## Recommended Resolution

Adopt two small adapters behind one `PaperDiscoveryProvider` boundary:

1. **OpenAlex is the first-version topic-search provider.** Query
   `/works?search=...` with a free server-side API key; return a bounded,
   paginated set of Candidate Papers, with OA/PDF availability shown as
   provider metadata rather than evidence or a licensing claim.
2. **arXiv is the first direct-import provider.** Search it independently for
   arXiv coverage and, after the user explicitly selects a result, import its
   documented PDF link into private workspace storage for personal/research
   use. Keep the abstract URL and versioned PDF URL in the provenance record.
3. **OpenAlex PDF import is a guarded fallback, not the first content API.**
   After explicit selection, try only a provider-supplied OA PDF URL (prefer a
   best OA location) and verify the actual response before accepting it. Do
   not use OpenAlex's paid cached-PDF endpoint in v1. A later ticket may add
   host-specific adapters once a source has been reviewed.

For every selected import, download server-side with a size/time limit and
redirect limit; accept only a successful final response whose content type is
`application/pdf` (allowing a documented host exception only after inspection)
and whose first bytes identify a PDF. Record provider, provider work ID,
canonical landing URL, requested and final download URLs, retrieval time,
declared OA/licence metadata, SHA-256, and import outcome. Only a successful
PDF makes a user-selected paper eligible for parsing, indexing, retrieval, or
citation. A user may still select an unavailable candidate to keep its metadata
in the workspace, but it remains `not_auto_importable` / `import_failed` and
is never evidence until an authorised PDF is supplied.

| Situation | Required behaviour |
| --- | --- |
| No discovery matches | Show an empty Candidate Paper state; offer upload, without creating an evidence source. |
| Provider outage, timeout, `429`, or arXiv rate limit | Keep existing candidates, show retryable provider status, apply bounded exponential backoff, and never fabricate a result. |
| OpenAlex `301` merged work / duplicate providers | Follow the merge; deduplicate by normalized DOI first, then arXiv ID, then provider ID. Display one candidate with all source links; never index a paper twice in one workspace. |
| Missing PDF or non-OA/restricted landing page | Keep metadata and external link; if chosen, retain it as a Selected Paper marked `not_auto_importable` and invite an authorised upload. |
| Redirect loop, non-2xx, HTML/login page, wrong MIME/signature, oversized PDF, or parse failure | Mark the chosen paper `import_failed` with a safe reason and retry action; retain metadata/link but create no chunks or citations. |
| Existing imported paper | Reuse the existing private file only when its recorded canonical identity and hash match; otherwise require an explicit replace/new-version action and retain provenance for the prior copy. |

This resolves the ticket's adapter choice and operational boundary. The
workspace/provenance-contract ticket must turn the recorded identity, import
states, and duplicate rules into durable domain fields before implementation.
