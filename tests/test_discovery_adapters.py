from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
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
    assert error.value.next_action == "configure_openalex_api_key"


def test_openalex_rate_limit_exposes_retry_after_header() -> None:
    with pytest.raises(DiscoveryProviderError) as error:
        OpenAlexProvider(
            api_key="server-only",
            requester=lambda *_args, **_kwargs: FakeResponse(
                status_code=429,
                headers={"Retry-After": "37"},
            ),
            retry_attempts=2,
            min_interval=0,
        ).search("evidence")

    assert error.value.retry_after_seconds == 37
    assert error.value.next_action == "retry_after_reset"


def test_openalex_auth_failure_requests_key_without_echoing_credentials() -> None:
    with pytest.raises(DiscoveryProviderError) as error:
        OpenAlexProvider(
            requester=lambda *_args, **_kwargs: FakeResponse(status_code=403),
            api_key="server-only-secret",
            retry_attempts=0,
        ).search("evidence")

    assert error.value.category == "provider_auth_required"
    assert error.value.next_action == "configure_openalex_api_key"
    assert "server-only-secret" not in str(error.value)


def test_openalex_honours_key_uses_per_page_caches_and_maps_multiple_pdf_locations() -> None:
    calls = []

    def request(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            payload={
                "meta": {"count": 1},
                "results": [
                    {
                        "id": "https://openalex.org/W456",
                        "title": "Cached paper",
                        "authorships": [],
                        "locations": [
                            {"pdf_url": "https://repository.example/first.pdf"},
                            {"pdf_url": "https://repository.example/second.pdf"},
                        ],
                        "best_oa_location": {"pdf_url": "https://repository.example/first.pdf"},
                        "open_access": {"is_oa": True},
                    }
                ],
            }
        )

    provider = OpenAlexProvider(
        api_key="server-only",
        requester=request,
        min_interval=0,
        cache_ttl=600,
    )
    first = provider.search("evidence", per_page=5)
    second = provider.search("evidence", per_page=5)

    assert first.candidates[0].pdf_urls == [
        "https://repository.example/first.pdf",
        "https://repository.example/second.pdf",
    ]
    assert second.candidates[0].provider_id == "W456"
    assert len(calls) == 1
    assert calls[0][1]["params"]["api_key"] == "server-only"
    assert calls[0][1]["params"]["per_page"] == 5


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
        min_interval=0,
        sleeper=delays.append,
    ).search("evidence")

    assert page.candidates == []
    assert delays == [0.25]


def test_openalex_minimum_interval_applies_between_transient_retries() -> None:
    now = [0.0]
    request_times: list[float] = []
    responses = iter(
        [
            FakeResponse(status_code=503),
            FakeResponse(payload={"meta": {"count": 0}, "results": []}),
        ]
    )

    def request(*_args, **_kwargs):
        request_times.append(now[0])
        return next(responses)

    def sleep(delay: float) -> None:
        now[0] += delay

    OpenAlexProvider(
        requester=request,
        retry_delay=0.25,
        min_interval=1.0,
        clock=lambda: now[0],
        sleeper=sleep,
    ).search("evidence")

    assert request_times[1] - request_times[0] >= 1.0


def test_openalex_coalesces_concurrent_identical_searches() -> None:
    calls = 0
    started = threading.Event()
    release = threading.Event()

    def request(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        started.set()
        release.wait(timeout=2)
        return FakeResponse(payload={"meta": {"count": 0}, "results": []})

    provider = OpenAlexProvider(requester=request, min_interval=0)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(provider.search, "evidence")
        assert started.wait(timeout=2)
        second = executor.submit(provider.search, "evidence")
        time.sleep(0.05)
        release.set()
        first.result(timeout=2)
        second.result(timeout=2)

    assert calls == 1


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


def test_pdf_downloader_accepts_pdf_signature_without_content_type(tmp_path: Path) -> None:
    downloader = RequestsPdfDownloader(
        requester=lambda *_args, **_kwargs: FakeResponse(body=b"%PDF-without-content-type")
    )

    result = downloader.download("https://example.test/paper", tmp_path / "paper.pdf")

    assert result.content_sha256
    assert (tmp_path / "paper.pdf").read_bytes().startswith(b"%PDF-")
