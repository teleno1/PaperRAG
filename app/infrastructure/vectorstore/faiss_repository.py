from __future__ import annotations

import json
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
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._metadata_path.parent.mkdir(parents=True, exist_ok=True)

        vector_array = np.array(vectors).astype("float32")
        embed_dim = int(vector_array.shape[1]) if len(vector_array.shape) == 2 and vector_array.shape[0] > 0 else self._embed_dim
        index = faiss.IndexFlatL2(embed_dim)
        if len(vector_array):
            index.add(vector_array)
        self._index_path.write_bytes(faiss.serialize_index(index).tobytes())
        self._metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        self._index = index
        self._metadata = metadata

    def count(self) -> int:
        if not self.exists():
            return 0
        self.load()
        return int(self._index.ntotal)

    def search(self, query_vector, top_k: int):
        self.load()
        return self._index.search(query_vector, top_k)

    @property
    def metadata(self) -> list[dict]:
        self.load()
        return self._metadata or []
