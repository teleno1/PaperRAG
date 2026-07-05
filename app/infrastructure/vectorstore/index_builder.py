from __future__ import annotations

from pathlib import Path

from app.core.processed_corpus import find_content_manifest
from app.domain.models.adapters import chunk_to_document_chunk
from app.domain.models.chunk import Chunk
from app.infrastructure.chunking.chunk_builder import ChunkBuilder
from app.infrastructure.parsing import MarkdownParser, MinerUParser, ParserRegistry, TxtParser
from app.infrastructure.llm.clients import DashScopeEmbeddingClient

BATCH_SIZE = 10


class IndexBuilder:
    def __init__(
        self,
        chunk_builder: ChunkBuilder | None = None,
        embedding_client: DashScopeEmbeddingClient | None = None,
        parser_registry: ParserRegistry | None = None,
    ) -> None:
        self._chunk_builder = chunk_builder or ChunkBuilder()
        self._embedding_client = embedding_client or DashScopeEmbeddingClient()
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

    def _build_chunk_embeddings(
        self,
        chunks: list[Chunk],
        *,
        paper_id: str,
        source_path: str,
        document_id: str | None = None,
        source_type: str = "pdf",
        extra_metadata: dict | None = None,
    ) -> tuple[list[list[float]], list[dict]]:
        embeddings: list[list[float]] = []
        metadata: list[dict] = []
        texts = [chunk.content for chunk in chunks]

        for start in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[start : start + BATCH_SIZE]
            batch_embeddings = self._embedding_client.embed_texts(batch_texts)
            batch_chunks = chunks[start : start + BATCH_SIZE]
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
        return {
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
