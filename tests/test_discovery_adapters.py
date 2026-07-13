from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.discovery import (
    ArxivProvider,
    DiscoveryProviderError,
    OpenAlexProvider,
    PdfDownloadError,
    RequestsPdfDownloader,
)


class FakeResponse:
    def __init__(self, *, payload=None, status_code: int = 200, headers=None, body: bytes = b"") -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.history = []
        self._body = body
        self.text = body.decode("utf-8")

    def json(self):
        return self._payload

    def iter_content(self, chunk_size: int):
        yield self._body


def test_openalex_adapter_maps_metadata_and_oa_pdf_provenance() -> None:
    calls = []

    def request(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            payload={
                "meta": {"count": 1},
                "results": [
                    {
                        "id": "https://openalex.org/W123",
                        "ids": {"arxiv": "https://arxiv.org/abs/2401.00001v2"},
                        "doi": "https://doi.org/10.1111/ABC",
                        "title": "A study",
                        "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
                        "publication_year": 2024,
                        "publication_date": "2024-05-06",
                        "updated_date": "2024-05-07",
                        "primary_location": {"source": {"display_name": "Open Venue"}},
                        "best_oa_location": {
                            "landing_page_url": "https://example.test/study",
                            "pdf_url": "https://example.test/study.pdf",
                            "license": "cc-by",
                        },
                        "open_access": {"is_oa": True},
                        "abstract_inverted_index": {"useful": [1], "A": [0], "abstract.": [2]},
                    }
                ],
            }
        )

    page = OpenAlexProvider(api_key="server-only", requester=request).search("evidence", per_page=5)

    assert calls[0][1]["params"]["api_key"] == "server-only"
    assert page.candidates[0].provider_id == "W123"
    assert page.candidates[0].doi == "10.1111/abc"
    assert page.candidates[0].arxiv_id == "2401.00001"
    assert page.candidates[0].abstract == "A useful abstract."
    assert page.candidates[0].is_open_access is True
    assert page.candidates[0].pdf_url == "https://example.test/study.pdf"
    assert page.candidates[0].published_at == "2024-05-06"
    assert page.candidates[0].source_updated_at == "2024-05-07"


def test_openalex_rate_limit_is_a_retryable_provider_error() -> None:
    with pytest.raises(DiscoveryProviderError) as error:
        OpenAlexProvider(
            requester=lambda *_args, **_kwargs: FakeResponse(status_code=429),
            retry_attempts=0,
        ).search("evidence")

    assert error.value.category == "provider_rate_limited"
    assert error.value.retryable is True


def test_openalex_retries_transient_failures_with_bounded_backoff() -> None:
    responses = iter(
        [
            FakeResponse(status_code=503),
            FakeResponse(payload={"meta": {"count": 0}, "results": []}),
        ]
    )
    delays: list[float] = []

    page = OpenAlexProvider(
        requester=lambda *_args, **_kwargs: next(responses),
        retry_delay=0.25,
        sleeper=delays.append,
    ).search("evidence")

    assert page.candidates == []
    assert delays == [0.25]


def test_arxiv_adapter_maps_public_pdf_link_without_claiming_a_license() -> None:
    atom = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
      <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:totalResults>
      <entry><id>https://arxiv.org/abs/2401.00001v2</id><title> A paper </title>
      <summary> A summary. </summary><published>2024-01-01T00:00:00Z</published>
      <updated>2024-01-02T00:00:00Z</updated>
      <author><name>Ada Lovelace</name></author><category term="cs.AI"/>
      <link title="pdf" type="application/pdf" href="https://arxiv.org/pdf/2401.00001v2"/></entry>
    </feed>"""

    page = ArxivProvider(requester=lambda *_args, **_kwargs: FakeResponse(body=atom.encode()), min_interval=0).search("RAG")

    candidate = page.candidates[0]
    assert candidate.arxiv_id == "2401.00001"
    assert candidate.is_open_access is None
    assert candidate.license is None
    assert candidate.pdf_url == "https://arxiv.org/pdf/2401.00001v2"
    assert candidate.published_at == "2024-01-01T00:00:00Z"
    assert candidate.source_updated_at == "2024-01-02T00:00:00Z"


def test_arxiv_adapter_caches_repeated_query_results() -> None:
    calls = 0

    def request(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return FakeResponse(body=b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"/>''')

    provider = ArxivProvider(requester=request, min_interval=0)
    provider.search("RAG")
    provider.search("rag")

    assert calls == 1


def test_pdf_downloader_rejects_html_even_when_the_url_is_public(tmp_path: Path) -> None:
    downloader = RequestsPdfDownloader(
        requester=lambda *_args, **_kwargs: FakeResponse(
            headers={"content-type": "text/html"},
            body=b"<html>login</html>",
        )
    )

    with pytest.raises(PdfDownloadError, match="did not return a PDF"):
        downloader.download("https://example.test/login", tmp_path / "paper.pdf")


def test_pdf_downloader_requires_pdf_signature_at_file_start(tmp_path: Path) -> None:
    downloader = RequestsPdfDownloader(
        requester=lambda *_args, **_kwargs: FakeResponse(
            headers={"content-type": "application/pdf"},
            body=b"prefix%PDF-not-a-header",
        )
    )

    with pytest.raises(PdfDownloadError, match="valid PDF"):
        downloader.download("https://example.test/paper.pdf", tmp_path / "paper.pdf")


def test_pdf_downloader_records_final_url_and_content_hash(tmp_path: Path) -> None:
    body = b"%PDF-verified"
    downloader = RequestsPdfDownloader(
        requester=lambda *_args, **_kwargs: FakeResponse(
            headers={"content-type": "application/pdf"},
            body=body,
        )
    )

    result = downloader.download("https://example.test/paper.pdf", tmp_path / "paper.pdf")

    assert result.requested_url == "https://example.test/paper.pdf"
    assert result.final_url == result.requested_url
    assert result.content_sha256 == "18a44e4002150c81914ba84bad719bc41fed145fd948ca072289ba35e2bb7141"
    assert (tmp_path / "paper.pdf").read_bytes() == body
