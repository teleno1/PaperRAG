from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.core.processed_corpus import find_content_manifest
from app.domain.models.adapters import chunk_to_document_chunk
from app.domain.models.chunk import Chunk
from app.infrastructure.chunking.chunk_builder import ChunkBuilder
from app.infrastructure.parsing import MarkdownParser, MinerUParser, ParserRegistry, TxtParser
from app.infrastructure.llm.clients import DashScopeEmbeddingClient

BATCH_SIZE = 10


@dataclass(slots=True)
class WorkspaceIndexEntry:
    workspace_id: str
    paper_id: str
    document_version_id: str
    source_path: str
    chunks: list[Chunk]


class IndexBuilder:
    def __init__(
        self,
        chunk_builder: ChunkBuilder | None = None,
        embedding_client: DashScopeEmbeddingClient | None = None,
        parser_registry: ParserRegistry | None = None,
        expected_embedding_dimension: int | None = None,
    ) -> None:
        self._chunk_builder = chunk_builder or ChunkBuilder()
        self._embedding_client = embedding_client or DashScopeEmbeddingClient()
        self._expected_embedding_dimension = expected_embedding_dimension
        self._parser_registry = parser_registry or ParserRegistry(
            parsers=[TxtParser(), MarkdownParser(), MinerUParser()]
        )

    def _iter_corpus_files(self, processed_dir: Path) -> list[Path]:
        paths: list[Path] = []
        for paper_dir in sorted(processed_dir.iterdir()):
            if not paper_dir.is_dir():
                continue
            json_path = find_content_manifest(paper_dir)
            if json_path is not None:
                paths.append(json_path)
        return paths

    def build(self, processed_dir: Path) -> tuple[list[list[float]], list[dict]]:
        all_embeddings: list[list[float]] = []
        all_metadata: list[dict] = []

        for json_path in self._iter_corpus_files(processed_dir):
            paper_id = json_path.parent.name
            chunks = self._chunk_builder.build_chunks(json_path)
            embeddings, metadata = self._build_chunk_embeddings(
                chunks,
                paper_id=paper_id,
                source_path=str(json_path),
            )
            all_embeddings.extend(embeddings)
            all_metadata.extend(metadata)

        return all_embeddings, all_metadata

    def _iter_source_files(self, source_dir: Path) -> list[Path]:
        supported_extensions = set(self._parser_registry.supported_extensions())
        return [
            path
            for path in sorted(source_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in supported_extensions
        ]

    def build_from_source_dir(self, source_dir: Path) -> tuple[list[list[float]], list[dict]]:
        all_embeddings: list[list[float]] = []
        all_metadata: list[dict] = []

        for source_path in self._iter_source_files(source_dir):
            parsed_document = self._parser_registry.parse(source_path)
            chunks = self._chunk_builder.build_chunks_from_parsed_document(parsed_document)
            embeddings, metadata = self._build_chunk_embeddings(
                chunks,
                paper_id=parsed_document.document_id,
                document_id=parsed_document.document_id,
                source_path=str(source_path),
                source_type=parsed_document.source_type,
                extra_metadata=parsed_document.metadata,
            )
            all_embeddings.extend(embeddings)
            all_metadata.extend(metadata)

        return all_embeddings, all_metadata

    def build_workspace(
        self,
        entries: list[WorkspaceIndexEntry],
        *,
        progress_callback: Callable[[int], None] | None = None,
    ) -> tuple[list[list[float]], list[dict]]:
        """Embed only the active ready versions belonging to one workspace."""

        all_embeddings: list[list[float]] = []
        all_metadata: list[dict] = []
        completed = 0
        for entry in entries:
            embeddings, metadata = self._build_chunk_embeddings(
                entry.chunks,
                paper_id=entry.paper_id,
                document_id=entry.document_version_id,
                source_path=entry.source_path,
                source_type="pdf",
                extra_metadata={"workspace_id": entry.workspace_id},
                progress_callback=(
                    (lambda count, offset=completed: progress_callback(offset + count))
                    if progress_callback is not None
                    else None
                ),
            )
            all_embeddings.extend(embeddings)
            all_metadata.extend(metadata)
            completed += len(metadata)
        return all_embeddings, all_metadata

    def _build_chunk_embeddings(
        self,
        chunks: list[Chunk],
        *,
        paper_id: str,
        source_path: str,
        document_id: str | None = None,
        source_type: str = "pdf",
        extra_metadata: dict | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> tuple[list[list[float]], list[dict]]:
        embeddings: list[list[float]] = []
        metadata: list[dict] = []
        texts = [chunk.content for chunk in chunks]

        for start in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[start : start + BATCH_SIZE]
            batch_embeddings = self._embedding_client.embed_texts(batch_texts)
            batch_chunks = chunks[start : start + BATCH_SIZE]
            if len(batch_embeddings) != len(batch_chunks):
                raise ValueError(
                    "embedding provider returned a different number of vectors than requested"
                )
            dimensions = {
                len(vector)
                for vector in batch_embeddings
                if isinstance(vector, (list, tuple)) and vector
            }
            if len(dimensions) != 1 or any(
                not isinstance(vector, (list, tuple)) or not vector for vector in batch_embeddings
            ):
                raise ValueError("embedding provider returned invalid vectors")
            dimension = next(iter(dimensions))
            if self._expected_embedding_dimension is not None and dimension != self._expected_embedding_dimension:
                raise ValueError(
                    "embedding provider returned vectors with an unexpected dimension"
                )
            for offset, (embedding, chunk) in enumerate(zip(batch_embeddings, batch_chunks)):
                chunk_index = start + offset
                embeddings.append(embedding)
                metadata.append(
                    self._chunk_to_metadata(
                        chunk,
                        paper_id=paper_id,
                        chunk_index=chunk_index,
                        source_path=source_path,
                        document_id=document_id,
                        source_type=source_type,
                        extra_metadata=extra_metadata,
                    )
                )
            if progress_callback is not None:
                progress_callback(start + len(batch_chunks))
        return embeddings, metadata

    @staticmethod
    def _chunk_to_metadata(
        chunk: Chunk,
        paper_id: str,
        chunk_index: int,
        source_path: str,
        *,
        document_id: str | None = None,
        source_type: str = "pdf",
        extra_metadata: dict | None = None,
    ) -> dict:
        document_chunk = chunk_to_document_chunk(
            chunk,
            paper_id=paper_id,
            document_id=document_id,
            chunk_index=chunk_index,
            source_path=source_path,
            source_type=source_type,
            extra_metadata=extra_metadata,
        )
        metadata = {
            "content": document_chunk.content,
            "section": document_chunk.section,
            "title": chunk.title,
            "authors": chunk.authors,
            "year": chunk.year,
            "venue": chunk.venue,
            "document_id": document_chunk.document_id,
            "source_path": document_chunk.source_path,
            "source_type": document_chunk.source_type,
            "source_dir": paper_id,
            "paper_id": paper_id,
            "chunk_id": document_chunk.chunk_id,
        }
        if chunk.source_anchor is not None:
            metadata.update(
                {
                    "workspace_id": (extra_metadata or {}).get("workspace_id"),
                    "document_version_id": chunk.source_anchor.document_version_id,
                    "page_start": chunk.source_anchor.page_start,
                    "page_end": chunk.source_anchor.page_end,
                    "character_start": chunk.source_anchor.character_start,
                    "character_end": chunk.source_anchor.character_end,
                    "excerpt": chunk.source_anchor.excerpt,
                    "source_anchor": chunk.source_anchor.to_dict(),
                }
            )
            if metadata["workspace_id"] is None:
                metadata.pop("workspace_id")
        return metadata
