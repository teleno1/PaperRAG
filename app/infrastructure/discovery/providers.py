from __future__ import annotations

import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import Future
from typing import Any, Callable, Protocol

import requests

from app.domain.workspace import DiscoveryCandidate, DiscoveryPage


class DiscoveryProviderError(RuntimeError):
    """A provider failed without exposing its response body to the user."""

    def __init__(
        self,
        category: str,
        message: str,
        *,
        retryable: bool = True,
        retry_after_seconds: int | None = None,
        next_action: str | None = None,
    ) -> None:
        self.category = category
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.next_action = next_action
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
        cache_ttl: float = 600.0,
        min_interval: float = 1.0,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._requester = requester or requests.get
        self._timeout = timeout
        self._retry_attempts = max(retry_attempts, 0)
        self._retry_delay = max(retry_delay, 0.0)
        self._cache_ttl = max(cache_ttl, 0.0)
        self._min_interval = max(min_interval, 0.0)
        self._clock = clock or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._cache: dict[tuple[str, int, int], tuple[float, DiscoveryPage]] = {}
        self._inflight: dict[tuple[str, int, int], Future[DiscoveryPage]] = {}
        self._last_request: float | None = None
        self._lock = threading.Lock()

    def _wait_for_rate_limit(self) -> None:
        with self._lock:
            now = self._clock()
            if self._last_request is not None:
                remaining = self._min_interval - (now - self._last_request)
                if remaining > 0:
                    self._sleeper(remaining)
            self._last_request = self._clock()

    @staticmethod
    def _header(response: Any, name: str) -> str | None:
        headers = getattr(response, "headers", {}) or {}
        for key, value in headers.items():
            if str(key).lower() == name.lower():
                return str(value)
        return None

    @classmethod
    def _retry_after(cls, response: Any) -> int | None:
        retry_after = cls._header(response, "retry-after")
        if retry_after:
            try:
                return max(int(float(retry_after)), 1)
            except ValueError:
                pass
        reset = cls._header(response, "x-ratelimit-reset")
        if not reset:
            return None
        try:
            reset_value = int(float(reset))
        except ValueError:
            return None
        # Providers commonly expose either a delay or a Unix timestamp here.
        if reset_value > int(time.time()) + 60:
            return max(reset_value - int(time.time()), 1)
        return max(reset_value, 1)

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
        cache_key = (normalized_query.casefold(), page, per_page)
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None and self._clock() - cached[0] < self._cache_ttl:
                return cached[1]
            future = self._inflight.get(cache_key)
            owner = future is None
            if owner:
                future = Future()
                self._inflight[cache_key] = future
        if not owner:
            return future.result()
        try:
            result = self._search_uncached(
                normalized_query,
                page=page,
                per_page=per_page,
                cache_key=cache_key,
            )
        except BaseException as exc:
            future.set_exception(exc)
            raise
        else:
            future.set_result(result)
            return result
        finally:
            with self._lock:
                self._inflight.pop(cache_key, None)

    def _search_uncached(
        self,
        normalized_query: str,
        *,
        page: int,
        per_page: int,
        cache_key: tuple[str, int, int],
    ) -> DiscoveryPage:
        params = {
            "search": normalized_query,
            "page": page,
            "per_page": min(max(per_page, 1), 50),
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
                    "locations",
                    "has_content",
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
            self._wait_for_rate_limit()
            try:
                response = self._requester(self._base_url, params=params, timeout=self._timeout)
            except requests.RequestException as exc:
                if attempt >= self._retry_attempts:
                    raise DiscoveryProviderError("provider_unavailable", "OpenAlex is temporarily unavailable.") from exc
                self._sleeper(min(self._retry_delay * (2**attempt), 2.0))
                continue
            status_code = getattr(response, "status_code", 200)
            transient = 500 <= status_code < 600
            if not transient or attempt >= self._retry_attempts:
                break
            self._sleeper(min(self._retry_delay * (2**attempt), 2.0))
        if response is None:
            raise DiscoveryProviderError("provider_unavailable", "OpenAlex is temporarily unavailable.")
        status_code = getattr(response, "status_code", 200)
        if status_code == 429:
            retry_after = self._retry_after(response)
            message = "OpenAlex rate limit reached; configure OPENALEX_API_KEY or retry after the reset window."
            raise DiscoveryProviderError(
                "provider_rate_limited",
                message,
                retry_after_seconds=retry_after,
                next_action="configure_openalex_api_key" if not self._api_key else "retry_after_reset",
            )
        if status_code >= 500:
            raise DiscoveryProviderError("provider_unavailable", "OpenAlex is temporarily unavailable.")
        if status_code in {401, 403}:
            raise DiscoveryProviderError(
                "provider_auth_required",
                "OpenAlex requires an API key for this request.",
                retryable=False,
                next_action="configure_openalex_api_key",
            )
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
            locations = [
                location
                for location in [best_location, primary_location, *(work.get("locations") or [])]
                if isinstance(location, dict) and location.get("is_oa") is not False
            ]
            pdf_urls: list[str] = []
            for location in locations:
                pdf_url = location.get("pdf_url")
                if pdf_url and pdf_url not in pdf_urls:
                    pdf_urls.append(pdf_url)
            source = best_location.get("source") or primary_location.get("source") or {}
            landing_url = best_location.get("landing_page_url") or primary_location.get("landing_page_url")
            pdf_url = pdf_urls[0] if pdf_urls else None
            arxiv_url = (work.get("ids") or {}).get("arxiv")
            arxiv_id = str(arxiv_url or "").rstrip("/").split("/")[-1] or None
            provider_id = str(work.get("id") or "").rstrip("/").split("/")[-1]
            if not provider_id:
                continue
            source_links = [link for link in (landing_url, *pdf_urls, work.get("id")) if link]
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
                    pdf_urls=pdf_urls,
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
        page_result = DiscoveryPage(
            provider=self.name,
            query=normalized_query,
            candidates=candidates,
            page=page,
            per_page=per_page,
            total_count=total_count,
            next_page=next_page,
        )
        with self._lock:
            self._cache[cache_key] = (self._clock(), page_result)
        return page_result


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
                    pdf_urls=[pdf_link] if pdf_link else [],
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
