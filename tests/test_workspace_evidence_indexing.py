from __future__ import annotations

from pathlib import Path

import numpy as np

from app.domain.models import ParsedDocument, ParsedDocumentUnit
from app.domain.literature_report import SourceChunk
from app.api.routes.workspaces import _source_chunk_response
from app.infrastructure.chunking import ChunkBuilder
from app.infrastructure.parsing import ParserRegistry
from app.infrastructure.vectorstore.faiss_repository import FaissRepository
from app.infrastructure.workspace.repository import WorkspaceRepository
from app.use_cases.workspace import ResearchWorkspaceService


class FakePdfParser:
    source_type = "pdf"
    supported_extensions = (".pdf",)

    def parse(self, source_path: Path, *, document_id: str | None = None) -> ParsedDocument:
        return ParsedDocument(
            document_id=document_id or "version",
            source_path=str(source_path),
            source_type="pdf",
            units=[
                ParsedDocumentUnit(
                    content="第一段说明证据边界。第二句跨越页面并保留位置。",
                    section="方法",
                    page_number=1,
                    metadata={"character_start": 0, "character_end": 22},
                ),
                ParsedDocumentUnit(
                    content="第三句继续说明检索过程。第四句提供结果。",
                    section="方法",
                    page_number=2,
                    metadata={"character_start": 23, "character_end": 43},
                ),
            ],
            metadata={"parser": "controlled", "parser_version": "test-1"},
        )


class StableEmbeddingClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider unavailable")
        return [[float(len(text))] + [1.0] * 1023 for text in texts]

    def embed_query(self, query: str) -> np.ndarray:
        return np.asarray(self.embed_texts([query]), dtype="float32")


def build_service(tmp_path: Path, embedding_client: StableEmbeddingClient) -> ResearchWorkspaceService:
    return ResearchWorkspaceService(
        repository=WorkspaceRepository(tmp_path / "workspace.sqlite3"),
        parser_registry=ParserRegistry([FakePdfParser()]),
        storage_root=tmp_path / "workspace-files",
        embedding_client=embedding_client,
    )


def index_repository(service: ResearchWorkspaceService, workspace_id: str, root: Path) -> FaissRepository:
    return FaissRepository(
        index_path=root / workspace_id / "index" / "evidence.faiss",
        metadata_path=root / workspace_id / "index" / "metadata.json",
        embed_dim=1024,
    )


def test_chunk_builder_preserves_page_range_character_range_and_clean_excerpt() -> None:
    parsed = FakePdfParser().parse(Path("paper.pdf"), document_id="version-1")

    chunks = ChunkBuilder(max_tokens=100).build_chunks_from_parsed_document(parsed)

    assert chunks
    anchor = chunks[0].source_anchor
    assert anchor is not None
    assert anchor.document_version_id == "version-1"
    assert anchor.page_start == 1
    assert anchor.page_end == 2
    assert anchor.character_start == 0
    assert anchor.character_end == 43
    assert anchor.section == "方法"
    assert anchor.excerpt in chunks[0].content
    assert not anchor.excerpt.startswith("[Title:")


def test_selected_paper_is_ready_only_after_workspace_index_and_metadata_are_persisted(tmp_path: Path) -> None:
    service = build_service(tmp_path, StableEmbeddingClient())
    workspace = service.create_workspace(topic="证据溯源", report_language="zh")

    result = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")

    assert result.paper.evidence_eligible is True
    repository = index_repository(service, workspace.id, tmp_path / "workspace-files")
    assert repository.count() == 1
    metadata = repository.metadata[0]
    assert metadata["workspace_id"] == workspace.id
    assert metadata["paper_id"] == result.paper.id
    assert metadata["document_version_id"] == result.document_version_id
    assert metadata["source_anchor"]["section"] == "方法"
    assert metadata["source_anchor"]["excerpt"]
    assert result.operation is not None
    assert result.operation.total_work == 1
    assert result.operation.completed_work == 1


def test_workspace_retrieval_returns_the_saved_source_anchor(tmp_path: Path) -> None:
    service = build_service(tmp_path, StableEmbeddingClient())
    workspace = service.create_workspace(topic="retrieval", report_language="en")
    result = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")

    sources = service._evidence_retriever.search(
        papers=service.evidence_papers(workspace.id),
        query="evidence",
        top_k=1,
    )

    assert len(sources) == 1
    assert sources[0].document_version_id == result.document_version_id
    assert sources[0].source_anchor is not None
    assert sources[0].source_anchor["excerpt"] == sources[0].excerpt


def test_removed_ready_paper_is_not_left_in_workspace_index(tmp_path: Path) -> None:
    service = build_service(tmp_path, StableEmbeddingClient())
    workspace = service.create_workspace(topic="isolation", report_language="en")
    result = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")

    removed = service.remove_paper(workspace.id, result.paper.id)

    assert removed.evidence_eligible is False
    repository = index_repository(service, workspace.id, tmp_path / "workspace-files")
    assert repository.count() == 0
    assert repository.metadata == []


def test_embedding_failure_is_safe_and_retry_rebuilds_the_index(tmp_path: Path) -> None:
    embedding = StableEmbeddingClient(fail=True)
    service = build_service(tmp_path, embedding)
    workspace = service.create_workspace(topic="retry", report_language="en")

    first = service.upload_paper(workspace.id, filename="paper.pdf", content=b"%PDF-authorised")

    assert first.paper.evidence_readiness == "failed"
    assert first.paper.evidence_eligible is False
    assert first.operation is not None
    assert first.operation.error_category == "evidence_indexing_failed"
    assert first.operation.error_message != "provider unavailable"

    embedding.fail = False
    retried = service.retry_paper(workspace.id, first.paper.id)

    assert retried.paper.evidence_eligible is True
    repository = index_repository(service, workspace.id, tmp_path / "workspace-files")
    assert repository.count() == 1
    assert retried.operation is not None
    assert retried.operation.id != first.operation.id


def test_workspace_indexes_are_isolated(tmp_path: Path) -> None:
    service = build_service(tmp_path, StableEmbeddingClient())
    first = service.create_workspace(topic="first", report_language="en")
    second = service.create_workspace(topic="second", report_language="en")
    first_upload = service.upload_paper(first.id, filename="first.pdf", content=b"%PDF-authorised")
    second_upload = service.upload_paper(second.id, filename="second.pdf", content=b"%PDF-authorised")

    first_index = index_repository(service, first.id, tmp_path / "workspace-files")
    second_index = index_repository(service, second.id, tmp_path / "workspace-files")
    assert {item["workspace_id"] for item in first_index.metadata} == {first.id}
    assert {item["workspace_id"] for item in second_index.metadata} == {second.id}
    assert first_upload.paper.id not in {item["paper_id"] for item in second_index.metadata}
    assert second_upload.paper.id not in {item["paper_id"] for item in first_index.metadata}


def test_workspace_api_does_not_expose_source_filesystem_paths() -> None:
    response = _source_chunk_response(
        SourceChunk(
            id="chunk",
            workspace_id="workspace",
            paper_id="paper",
            document_version_id="version",
            chunk_id="chunk",
            title="Paper",
            excerpt="Evidence excerpt",
            source_anchor={
                "document_version_id": "version",
                "source_path": "C:/private/paper.pdf",
                "excerpt": "Evidence excerpt",
                "section": "Results",
                "page_start": 2,
                "page_end": 3,
            },
        )
    )

    assert response.source_anchor is not None
    assert "source_path" not in response.source_anchor
    assert response.source_anchor["document_version_id"] == "version"
