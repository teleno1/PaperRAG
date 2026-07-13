"""Open academic discovery adapters."""

from app.infrastructure.discovery.providers import (
    ArxivProvider,
    DiscoveryProviderError,
    OpenAlexProvider,
    PaperDiscoveryProvider,
)
from app.infrastructure.discovery.downloader import (
    PdfDownloadError,
    PdfDownloadResult,
    PdfDownloader,
    RequestsPdfDownloader,
)

__all__ = [
    "ArxivProvider",
    "DiscoveryProviderError",
    "OpenAlexProvider",
    "PaperDiscoveryProvider",
    "PdfDownloadError",
    "PdfDownloadResult",
    "PdfDownloader",
    "RequestsPdfDownloader",
]
