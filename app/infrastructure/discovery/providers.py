from __future__ import annotations

import threading
import time
import xml.etree.ElementTree as ET
from typing import Any, Callable, Protocol

import requests

from app.domain.workspace import DiscoveryCandidate, DiscoveryPage


class DiscoveryProviderError(RuntimeError):
    """A provider failed without exposing its response body to the user."""

    def __init__(self, category: str, message: str, *, retryable: bool = True) -> None:
        self.category = category
        self.retryable = retryable
        super().__init__(message)


class PaperDiscoveryProvider(Protocol):
    name: str

    def search(self, query: str, *, page: int = 1, per_page: int = 10) -> DiscoveryPage:
        """Return bounded Candidate Paper metadata for a topic query."""


Requester = Callable[..., Any]


class OpenAlexProvider:
    name = "openalex"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openalex.org/works",
        requester: Requester | None = None,
        timeout: float = 20.0,
        retry_attempts: int = 2,
        retry_delay: float = 0.25,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._requester = requester or requests.get
        self._timeout = timeout
        self._retry_attempts = max(retry_attempts, 0)
        self._retry_delay = max(retry_delay, 0.0)
        self._sleeper = sleeper or time.sleep

    @staticmethod
    def _abstract(inverted_index: dict[str, list[int]] | None) -> str:
        if not inverted_index:
            return ""
        # OpenAlex positions are sparse and may arrive in arbitrary JSON order.
        positioned = [(position, word) for word, positions in inverted_index.items() for position in positions]
        return " ".join(word for _, word in sorted(positioned))

    @staticmethod
    def _year(work: dict[str, Any]) -> str:
        publication_year = work.get("publication_year")
        if publication_year:
            return str(publication_year)
        publication_date = str(work.get("publication_date") or "")
        return publication_date[:4]

    def search(self, query: str, *, page: int = 1, per_page: int = 10) -> DiscoveryPage:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("discovery query must not be empty")
        params = {
            "search": normalized_query,
            "page": page,
            "per-page": min(max(per_page, 1), 50),
            "select": ",".join(
                [
                    "id",
                    "doi",
                    "title",
                    "authorships",
                    "publication_year",
                    "publication_date",
                    "updated_date",
                    "ids",
                    "primary_location",
                    "best_oa_location",
                    "open_access",
                    "abstract_inverted_index",
                    "is_retracted",
                ]
            ),
        }
        if self._api_key:
            params["api_key"] = self._api_key
        response = None
        for attempt in range(self._retry_attempts + 1):
            try:
                response = self._requester(self._base_url, params=params, timeout=self._timeout)
            except requests.RequestException as exc:
                if attempt >= self._retry_attempts:
                    raise DiscoveryProviderError("provider_unavailable", "OpenAlex is temporarily unavailable.") from exc
                self._sleeper(min(self._retry_delay * (2**attempt), 2.0))
                continue
            status_code = getattr(response, "status_code", 200)
            transient = status_code == 429 or 500 <= status_code < 600
            if not transient or attempt >= self._retry_attempts:
                break
            self._sleeper(min(self._retry_delay * (2**attempt), 2.0))
        if response is None:
            raise DiscoveryProviderError("provider_unavailable", "OpenAlex is temporarily unavailable.")
        status_code = getattr(response, "status_code", 200)
        if status_code == 429:
            raise DiscoveryProviderError("provider_rate_limited", "OpenAlex rate limit reached; retry later.")
        if status_code >= 500:
            raise DiscoveryProviderError("provider_unavailable", "OpenAlex is temporarily unavailable.")
        if status_code >= 400:
            raise DiscoveryProviderError(
                "provider_request_rejected",
                "OpenAlex rejected the discovery request.",
                retryable=False,
            )
        try:
            payload = response.json()
        except (ValueError, AttributeError) as exc:
            raise DiscoveryProviderError("provider_invalid_response", "OpenAlex returned an invalid response.") from exc

        candidates: list[DiscoveryCandidate] = []
        for work in payload.get("results", []):
            if work.get("is_retracted"):
                continue
            best_location = work.get("best_oa_location") or {}
            primary_location = work.get("primary_location") or {}
            source = best_location.get("source") or primary_location.get("source") or {}
            landing_url = best_location.get("landing_page_url") or primary_location.get("landing_page_url")
            pdf_url = best_location.get("pdf_url")
            arxiv_url = (work.get("ids") or {}).get("arxiv")
            arxiv_id = str(arxiv_url or "").rstrip("/").split("/")[-1] or None
            provider_id = str(work.get("id") or "").rstrip("/").split("/")[-1]
            if not provider_id:
                continue
            source_links = [link for link in (landing_url, pdf_url, work.get("id")) if link]
            candidates.append(
                DiscoveryCandidate(
                    provider=self.name,
                    provider_id=provider_id,
                    title=str(work.get("title") or "Untitled paper"),
                    authors=[
                        str(authorship.get("author", {}).get("display_name"))
                        for authorship in work.get("authorships", [])
                        if authorship.get("author", {}).get("display_name")
                    ],
                    abstract=self._abstract(work.get("abstract_inverted_index")),
                    year=self._year(work),
                    venue=str(source.get("display_name") or ""),
                    doi=work.get("doi"),
                    arxiv_id=arxiv_id,
                    source_url=landing_url or work.get("id"),
                    pdf_url=pdf_url,
                    published_at=work.get("publication_date"),
                    source_updated_at=work.get("updated_date"),
                    is_open_access=(work.get("open_access") or {}).get("is_oa"),
                    license=best_location.get("license"),
                    source_links=source_links,
                )
            )
        meta = payload.get("meta") or {}
        total_count = meta.get("count")
        next_page = page + 1 if total_count is not None and page * per_page < total_count else None
        return DiscoveryPage(
            provider=self.name,
            query=normalized_query,
            candidates=candidates,
            page=page,
            per_page=per_page,
            total_count=total_count,
            next_page=next_page,
        )


class ArxivProvider:
    name = "arxiv"
    _ATOM = "http://www.w3.org/2005/Atom"

    def __init__(
        self,
        *,
        base_url: str = "https://export.arxiv.org/api/query",
        requester: Requester | None = None,
        timeout: float = 30.0,
        min_interval: float = 3.0,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._base_url = base_url
        self._requester = requester or requests.get
        self._timeout = timeout
        self._min_interval = min_interval
        self._clock = clock or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._last_request: float | None = None
        self._lock = threading.Lock()
        self._cache: dict[tuple[str, int, int], DiscoveryPage] = {}

    def _wait_for_rate_limit(self) -> None:
        with self._lock:
            now = self._clock()
            if self._last_request is not None:
                remaining = self._min_interval - (now - self._last_request)
                if remaining > 0:
                    self._sleeper(remaining)
            self._last_request = self._clock()

    def search(self, query: str, *, page: int = 1, per_page: int = 10) -> DiscoveryPage:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("discovery query must not be empty")
        cache_key = (normalized_query.casefold(), page, per_page)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        self._wait_for_rate_limit()
        safe_query = normalized_query.replace('"', " ")
        params = {
            "search_query": f'all:"{safe_query}"',
            "start": max(page - 1, 0) * per_page,
            "max_results": min(max(per_page, 1), 50),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        try:
            response = self._requester(self._base_url, params=params, timeout=self._timeout)
        except requests.RequestException as exc:
            raise DiscoveryProviderError("provider_unavailable", "arXiv is temporarily unavailable.") from exc
        status_code = getattr(response, "status_code", 200)
        if status_code == 429 or status_code >= 500:
            raise DiscoveryProviderError("provider_rate_limited", "arXiv is temporarily unavailable; retry later.")
        if status_code >= 400:
            raise DiscoveryProviderError("provider_request_rejected", "arXiv rejected the discovery request.", retryable=False)
        try:
            root = ET.fromstring(response.text)
        except (AttributeError, ET.ParseError) as exc:
            raise DiscoveryProviderError("provider_invalid_response", "arXiv returned an invalid response.") from exc

        candidates: list[DiscoveryCandidate] = []
        for entry in root.findall(f"{{{self._ATOM}}}entry"):
            identifier = (entry.findtext(f"{{{self._ATOM}}}id") or "").strip()
            provider_id = identifier.rstrip("/").split("/")[-1]
            title = " ".join((entry.findtext(f"{{{self._ATOM}}}title") or "").split())
            if not provider_id or not title:
                continue
            links = entry.findall(f"{{{self._ATOM}}}link")
            pdf_link = next((link.attrib.get("href") for link in links if link.attrib.get("title") == "pdf"), None)
            source_link = identifier
            authors = [
                (author.findtext(f"{{{self._ATOM}}}name") or "").strip()
                for author in entry.findall(f"{{{self._ATOM}}}author")
            ]
            published_full = (entry.findtext(f"{{{self._ATOM}}}published") or "").strip()
            updated_full = (entry.findtext(f"{{{self._ATOM}}}updated") or "").strip() or None
            categories = entry.findall(f"{{{self._ATOM}}}category")
            venue = next((item.attrib.get("term", "") for item in categories if item.attrib.get("term")), "")
            candidates.append(
                DiscoveryCandidate(
                    provider=self.name,
                    provider_id=provider_id,
                    title=title,
                    authors=[author for author in authors if author],
                    abstract=" ".join((entry.findtext(f"{{{self._ATOM}}}summary") or "").split()),
                    year=published_full[:4],
                    published_at=published_full or None,
                    source_updated_at=updated_full,
                    venue=venue,
                    arxiv_id=provider_id,
                    source_url=source_link,
                    pdf_url=pdf_link,
                    is_open_access=None,
                    source_links=[link for link in (source_link, pdf_link) if link],
                )
            )
        total_results = root.findtext(f"{{{self._ATOM}}}totalResults")
        total_count = int(total_results) if total_results and total_results.isdigit() else None
        next_page = page + 1 if total_count is not None and page * per_page < total_count else None
        page_result = DiscoveryPage(
            provider=self.name,
            query=normalized_query,
            candidates=candidates,
            page=page,
            per_page=per_page,
            total_count=total_count,
            next_page=next_page,
        )
        self._cache[cache_key] = page_result
        return page_result
