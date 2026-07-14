from __future__ import annotations

import json
import os
from pathlib import Path

import faiss
import numpy as np


class FaissRepository:
    def __init__(self, index_path: Path, metadata_path: Path, embed_dim: int = 1024) -> None:
        self._index_path = index_path
        self._metadata_path = metadata_path
        self._embed_dim = embed_dim
        self._index = None
        self._metadata: list[dict] | None = None

    @property
    def index_path(self) -> Path:
        return self._index_path

    @property
    def metadata_path(self) -> Path:
        return self._metadata_path

    def exists(self) -> bool:
        return (
            self._index_path.exists()
            and self._metadata_path.exists()
            and self._index_path.stat().st_size > 0
            and self._metadata_path.stat().st_size > 0
        )

    def load(self) -> None:
        if self._index is None:
            self._index = faiss.deserialize_index(np.frombuffer(self._index_path.read_bytes(), dtype="uint8"))
        if self._metadata is None:
            self._metadata = json.loads(self._metadata_path.read_text(encoding="utf-8"))

    def save(self, vectors, metadata: list[dict]) -> None:
        if len(vectors) != len(metadata):
            raise ValueError("vector and metadata counts must match")
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._metadata_path.parent.mkdir(parents=True, exist_ok=True)

        vector_array = np.asarray(vectors, dtype="float32")
        if len(metadata) and (
            vector_array.ndim != 2
            or vector_array.shape[0] != len(metadata)
            or vector_array.shape[1] < 1
        ):
            raise ValueError("embedding vectors must be a non-empty 2D batch")
        embed_dim = int(vector_array.shape[1]) if len(vector_array.shape) == 2 and vector_array.shape[0] > 0 else self._embed_dim
        if vector_array.size and (len(vector_array.shape) != 2 or vector_array.shape[1] != embed_dim):
            raise ValueError("embedding vectors must have one consistent dimension")
        index = faiss.IndexFlatL2(embed_dim)
        if len(vector_array):
            index.add(vector_array)
        index_bytes = faiss.serialize_index(index).tobytes()
        index_tmp = self._index_path.with_suffix(self._index_path.suffix + ".tmp")
        metadata_tmp = self._metadata_path.with_suffix(self._metadata_path.suffix + ".tmp")
        index_tmp.write_bytes(index_bytes)
        metadata_tmp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(index_tmp, self._index_path)
        os.replace(metadata_tmp, self._metadata_path)
        self._index = index
        self._metadata = metadata

    def clear(self) -> None:
        """Remove this index atomically from the eligible evidence set."""

        self._index = None
        self._metadata = None
        for path in (self._index_path, self._metadata_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def count(self) -> int:
        if not self.exists():
            return 0
        self.load()
        return int(self._index.ntotal)

    def search(self, query_vector, top_k: int):
        self.load()
        return self._index.search(query_vector, min(max(top_k, 1), int(self._index.ntotal)))

    @property
    def metadata(self) -> list[dict]:
        if not self.exists():
            return []
        self.load()
        return self._metadata or []
