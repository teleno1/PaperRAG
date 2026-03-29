from __future__ import annotations

from typing import Protocol

from app.domain.retrieval.models import RetrievedSource


class RetrievalService(Protocol):
    def search(self, query: str, top_k: int = 20) -> list[RetrievedSource]:
        """Search sources for a query."""

