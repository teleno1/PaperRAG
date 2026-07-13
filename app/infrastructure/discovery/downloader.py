from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Callable, Protocol

import requests


class PdfDownloadError(RuntimeError):
    """A public candidate URL did not produce an acceptable PDF."""

    def __init__(self, category: str, message: str) -> None:
        self.category = category
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class PdfDownloadResult:
    requested_url: str
    final_url: str
    content_sha256: str
    downloaded_at: str


class PdfDownloader(Protocol):
    def download(self, url: str, destination: Path) -> PdfDownloadResult | None:
        """Download and verify one PDF into the managed destination."""


class RequestsPdfDownloader:
    """Bounded server-side PDF downloader for explicitly selected candidates."""

    def __init__(
        self,
        *,
        requester: Callable[..., Any] | None = None,
        timeout: float = 30.0,
        max_bytes: int = 25 * 1024 * 1024,
        max_redirects: int = 3,
    ) -> None:
        self._requester = requester or requests.get
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects

    def download(self, url: str, destination: Path) -> PdfDownloadResult:
        if not url.lower().startswith(("http://", "https://")):
            raise PdfDownloadError("invalid_source_url", "The candidate does not provide a valid public PDF URL.")
        try:
            response = self._requester(
                url,
                stream=True,
                timeout=self._timeout,
                allow_redirects=True,
                headers={
                    "Accept": "application/pdf, application/octet-stream;q=0.9, */*;q=0.1",
                    "User-Agent": "PaperRAG/0.1 (research workspace PDF importer)",
                },
            )
        except requests.RequestException as exc:
            raise PdfDownloadError("download_unavailable", "The public PDF could not be downloaded; retry later.") from exc
        if len(getattr(response, "history", [])) > self._max_redirects:
            raise PdfDownloadError("redirect_limit", "The public PDF redirected too many times.")
        status_code = getattr(response, "status_code", 0)
        if status_code < 200 or status_code >= 300:
            raise PdfDownloadError("download_failed", "The public PDF URL did not return a successful response.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        total = 0
        digest = hashlib.sha256()
        prefix = bytearray()
        content_type = str(getattr(response, "headers", {}).get("content-type", "")).split(";", 1)[0].strip().lower()
        try:
            with temporary.open("wb") as file_obj:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    if len(prefix) < 5:
                        prefix.extend(chunk[: 5 - len(prefix)])
                        if len(prefix) >= 5 and not bytes(prefix).startswith(b"%PDF-"):
                            message = (
                                "The selected public URL did not return a valid PDF."
                                if content_type == "application/pdf"
                                else "The selected public URL did not return a PDF."
                            )
                            raise PdfDownloadError("not_a_pdf", message)
                    total += len(chunk)
                    if total > self._max_bytes:
                        raise PdfDownloadError("pdf_too_large", "The selected PDF exceeds the workspace import limit.")
                    digest.update(chunk)
                    file_obj.write(chunk)
            with temporary.open("rb") as file_obj:
                if not file_obj.read(5).startswith(b"%PDF-"):
                    raise PdfDownloadError("not_a_pdf", "The selected public URL did not return a valid PDF.")
            temporary.replace(destination)
            return PdfDownloadResult(
                requested_url=url,
                final_url=str(getattr(response, "url", None) or url),
                content_sha256=digest.hexdigest(),
                downloaded_at=datetime.now(timezone.utc).isoformat(),
            )
        except PdfDownloadError:
            temporary.unlink(missing_ok=True)
            raise
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise PdfDownloadError("download_failed", "The public PDF could not be saved to the workspace.") from exc
