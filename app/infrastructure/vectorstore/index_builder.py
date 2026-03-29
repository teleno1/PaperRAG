from __future__ import annotations

from pathlib import Path

from app.domain.models.chunk import Chunk
from app.infrastructure.chunking.chunk_builder import ChunkBuilder
from app.infrastructure.llm.clients import DashScopeEmbeddingClient

BATCH_SIZE = 10


class IndexBuilder:
    def __init__(
        self,
        chunk_builder: ChunkBuilder | None = None,
        embedding_client: DashScopeEmbeddingClient | None = None,
    ) -> None:
        self._chunk_builder = chunk_builder or ChunkBuilder()
        self._embedding_client = embedding_client or DashScopeEmbeddingClient()

    def _iter_corpus_files(self, processed_dir: Path) -> list[Path]:
        paths: list[Path] = []
        for paper_dir in sorted(processed_dir.iterdir()):
            if not paper_dir.is_dir():
                continue
            json_path = paper_dir / "content_list_v2.json"
            if json_path.exists() and json_path.stat().st_size > 0:
                paths.append(json_path)
        return paths

    def build(self, processed_dir: Path) -> tuple[list[list[float]], list[dict]]:
        all_embeddings: list[list[float]] = []
        all_metadata: list[dict] = []

        for json_path in self._iter_corpus_files(processed_dir):
            paper_id = json_path.parent.name
            chunks = self._chunk_builder.build_chunks(json_path)
            texts = [chunk.content for chunk in chunks]

            for start in range(0, len(texts), BATCH_SIZE):
                batch_texts = texts[start : start + BATCH_SIZE]
                batch_embeddings = self._embedding_client.embed_texts(batch_texts)
                batch_chunks = chunks[start : start + BATCH_SIZE]
                for offset, (embedding, chunk) in enumerate(zip(batch_embeddings, batch_chunks)):
                    chunk_index = start + offset
                    all_embeddings.append(embedding)
                    all_metadata.append(self._chunk_to_metadata(chunk, paper_id=paper_id, chunk_index=chunk_index))

        return all_embeddings, all_metadata

    @staticmethod
    def _chunk_to_metadata(chunk: Chunk, paper_id: str, chunk_index: int) -> dict:
        return {
            "content": chunk.content,
            "section": chunk.section,
            "title": chunk.title,
            "authors": chunk.authors,
            "year": chunk.year,
            "venue": chunk.venue,
            "source_dir": paper_id,
            "paper_id": paper_id,
            "chunk_id": f"{paper_id}__chunk_{chunk_index:04d}",
        }
