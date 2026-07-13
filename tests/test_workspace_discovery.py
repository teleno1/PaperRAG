from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import InvalidPaperUploadError
from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.domain.workspace import DiscoveryCandidate, DiscoveryPage
from app.infrastructure.discovery import DiscoveryProviderError, PaperDiscoveryProvider, PdfDownloadError, PdfDownloader
from app.infrastructure.parsing import ParserRegistry
from app.infrastructure.workspace.repository import WorkspaceRepository
from app.use_cases.workspace import ResearchWorkspaceService


class FakePdfParser:
    source_type = "pdf"
    supported_extensions = (".pdf",)

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        return ParsedDocument(
            document_id=document_id or "document-version",
            source_path=str(source_path),
            source_type="pdf",
            units=[ParsedDocumentUnit(content="A paper paragraph.", section="Introduction", page_number=1)],
        )


class FakeDiscoveryProvider(PaperDiscoveryProvider):
    name = "fake"

    def __init__(self, candidates: list[DiscoveryCandidate], error: DiscoveryProviderError | None = None) -> None:
        self.candidates = candidates
        self.error = error

    def search(self, query: str, *, page: int = 1, per_page: int = 10) -> DiscoveryPage:
        if self.error is not None:
            raise self.error
        return DiscoveryPage(
            provider=self.name,
            query=query,
            candidates=self.candidates,
            page=page,
            per_page=per_page,
            total_count=len(self.candidates),
        )


class FakePdfDownloader(PdfDownloader):
    def __init__(self, error: PdfDownloadError | None = None) -> None:
        self.error = error

    def download(self, url: str, destination: Path) -> None:
        if self.error is not None:
            raise self.error
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"%PDF-downloaded")


def build_service(
    tmp_path: Path,
    provider: FakeDiscoveryProvider,
    downloader: PdfDownloader | None = None,
) -> ResearchWorkspaceService:
    return ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
        discovery_providers={provider.name: provider},
        pdf_downloader=downloader,
    )


def test_discovery_persists_candidate_metadata_without_making_it_evidence(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-1",
                title="Evidence Attribution",
                authors=["Ada Lovelace"],
                abstract="A useful abstract.",
                year="2024",
                venue="Research Venue",
                doi="https://doi.org/10.1000/ABC",
                source_url="https://example.test/paper",
                pdf_url="https://example.test/paper.pdf",
                is_open_access=True,
                license="cc-by",
            )
        ]
    )
    service = build_service(tmp_path, provider)
    workspace = service.create_workspace(topic="Evidence attribution", report_language="en")

    result = service.discover_papers(workspace.id, query="evidence attribution", provider="fake")

    assert result.status == "succeeded"
    candidate = result.candidates[0]
    assert candidate.source_kind == "discovery"
    assert candidate.selected is False
    assert candidate.title == "Evidence Attribution"
    assert candidate.abstract == "A useful abstract."
    assert candidate.provider == "fake"
    assert candidate.doi == "10.1000/abc"
    assert candidate.pdf_url == "https://example.test/paper.pdf"
    assert candidate.evidence_eligible is False
    assert service.evidence_papers(workspace.id) == []


def test_discovery_deduplicates_by_normalized_doi_and_keeps_candidate_visible(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-1",
                title="First title",
                doi="10.1000/ABC",
                source_url="https://example.test/first",
            ),
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-2",
                title="Second title",
                doi="https://doi.org/10.1000/abc",
                source_url="https://example.test/second",
            ),
        ]
    )
    service = build_service(tmp_path, provider)
    workspace = service.create_workspace(topic="Deduplication", report_language="en")

    result = service.discover_papers(workspace.id, query="deduplication", provider="fake")

    assert len(result.candidates) == 1
    assert len(service.get_workspace(workspace.id).papers) == 1
    assert result.candidates[0].source_links == [
        "https://example.test/first",
        "https://example.test/second",
    ]


def test_provider_outage_keeps_existing_candidates_and_reports_retryable_status(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [DiscoveryCandidate(provider="fake", provider_id="work-1", title="Existing candidate")]
    )
    service = build_service(tmp_path, provider)
    workspace = service.create_workspace(topic="Provider outage", report_language="en")
    service.discover_papers(workspace.id, provider="fake")
    provider.error = DiscoveryProviderError("provider_unavailable", "The provider is temporarily unavailable.")

    result = service.discover_papers(workspace.id, provider="fake")

    assert result.status == "retryable_error"
    assert result.retryable is True
    assert result.error_message == "The provider is temporarily unavailable."
    assert [paper.title for paper in result.candidates] == ["Existing candidate"]

    provider.error = DiscoveryProviderError("provider_request_rejected", "The provider rejected the query.", retryable=False)
    failed = service.discover_papers(workspace.id, provider="fake")

    assert failed.status == "failed"
    assert failed.retryable is False


def test_selecting_open_candidate_downloads_and_processes_it_as_evidence(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-1",
                title="Open Evidence Paper",
                pdf_url="https://example.test/open.pdf",
                is_open_access=True,
            )
        ]
    )
    downloader = FakePdfDownloader()
    service = build_service(tmp_path, provider, downloader)
    workspace = service.create_workspace(topic="Open evidence", report_language="en")
    candidate = service.discover_papers(workspace.id, provider="fake").candidates[0]

    imported = service.import_discovered_paper(workspace.id, candidate.id)

    paper = service.get_workspace(workspace.id).papers[0]
    assert imported.operation is not None
    assert imported.operation.status == "succeeded"
    assert paper.selected is True
    assert paper.evidence_readiness == "ready"
    assert paper.evidence_eligible is True
    assert service.evidence_papers(workspace.id)[0].id == paper.id


def test_restricted_candidate_stays_visible_and_requests_authorised_upload(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-1",
                title="Restricted Paper",
                source_url="https://example.test/restricted",
                pdf_url="https://example.test/login",
                is_open_access=False,
            )
        ]
    )
    downloader = FakePdfDownloader()
    service = build_service(tmp_path, provider, downloader)
    workspace = service.create_workspace(topic="Restricted evidence", report_language="en")
    candidate = service.discover_papers(workspace.id, provider="fake").candidates[0]

    selected = service.import_discovered_paper(workspace.id, candidate.id)

    assert selected.operation is None
    assert selected.paper.selected is True
    assert selected.paper.evidence_readiness == "awaiting_authorised_file"
    assert selected.paper.next_action == "upload_authorised_pdf"
    assert service.evidence_papers(workspace.id) == []


def test_authorised_upload_reuses_restricted_candidate_identity(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-1",
                title="Restricted Paper",
                doi="10.5555/restricted",
                is_open_access=False,
            )
        ]
    )
    service = build_service(tmp_path, provider)
    workspace = service.create_workspace(topic="Authorised recovery", report_language="en")
    candidate = service.discover_papers(workspace.id, provider="fake").candidates[0]

    uploaded = service.upload_paper(
        workspace.id,
        filename="authorised-copy.pdf",
        content=b"%PDF-authorised",
        candidate_id=candidate.id,
    )

    paper = service.get_workspace(workspace.id).papers[0]
    assert uploaded.operation.status == "succeeded"
    assert paper.id == candidate.id
    assert paper.title == "Restricted Paper"
    assert paper.doi == "10.5555/restricted"
    assert paper.source_kind == "discovery"
    assert paper.evidence_eligible is True


def test_discovered_download_failure_preserves_metadata_and_is_retryable(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-1",
                title="Broken Open Paper",
                pdf_url="https://example.test/broken.pdf",
                is_open_access=True,
            )
        ]
    )
    downloader = FakePdfDownloader(PdfDownloadError("not_a_pdf", "The selected public URL did not return a PDF."))
    service = build_service(tmp_path, provider, downloader)
    workspace = service.create_workspace(topic="Import failure", report_language="en")
    candidate = service.discover_papers(workspace.id, provider="fake").candidates[0]

    imported = service.import_discovered_paper(workspace.id, candidate.id)

    paper = service.get_workspace(workspace.id).papers[0]
    assert imported.operation is not None
    assert imported.operation.status == "failed"
    assert imported.operation.error_category == "not_a_pdf"
    assert paper.source_url is None
    assert paper.pdf_url == "https://example.test/broken.pdf"
    assert paper.evidence_readiness == "failed"
    assert paper.retryable is True
    assert paper.next_action == "retry_import"
    assert service.evidence_papers(workspace.id) == []


def test_replacing_ready_discovered_paper_requires_explicit_new_version_action(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-1",
                title="Replaceable Paper",
                pdf_url="https://example.test/paper.pdf",
                is_open_access=True,
            )
        ]
    )
    service = build_service(tmp_path, provider, FakePdfDownloader())
    workspace = service.create_workspace(topic="Version replacement", report_language="en")
    candidate = service.discover_papers(workspace.id, provider="fake").candidates[0]
    first = service.import_discovered_paper(workspace.id, candidate.id)

    with pytest.raises(InvalidPaperUploadError, match="replace=true"):
        service.import_discovered_paper(workspace.id, candidate.id)

    replacement = service.import_discovered_paper(workspace.id, candidate.id, replace=True)

    assert replacement.document_version_id != first.document_version_id
    assert replacement.operation.id != first.operation.id
    assert replacement.paper.evidence_eligible is True


def test_failed_replacement_preserves_previous_active_version(tmp_path: Path) -> None:
    provider = FakeDiscoveryProvider(
        [
            DiscoveryCandidate(
                provider="fake",
                provider_id="work-1",
                title="Stable Paper",
                pdf_url="https://example.test/paper.pdf",
                is_open_access=True,
            )
        ]
    )
    downloader = FakePdfDownloader()
    service = build_service(tmp_path, provider, downloader)
    workspace = service.create_workspace(topic="Atomic replacement", report_language="en")
    candidate = service.discover_papers(workspace.id, provider="fake").candidates[0]
    first = service.import_discovered_paper(workspace.id, candidate.id)
    previous_version_id = first.paper.active_document_version_id
    downloader.error = PdfDownloadError("download_failed", "The selected public PDF is unavailable.")

    failed = service.import_discovered_paper(workspace.id, candidate.id, replace=True)

    assert failed.operation.status == "failed"
    assert failed.paper.active_document_version_id == previous_version_id
    assert failed.paper.evidence_eligible is False
