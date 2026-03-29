from __future__ import annotations

import re
from collections import defaultdict

import numpy as np

from app.domain.retrieval.models import RetrievedSource
from app.domain.retrieval.service import RetrievalService
from app.infrastructure.llm.clients import DashScopeEmbeddingClient, DashScopeRerankClient
from app.infrastructure.vectorstore.faiss_repository import FaissRepository

SECTION_BONUS = {
    "abstract": 0.03,
    "introduction": 0.04,
    "background": 0.03,
    "related_work": 0.03,
    "method": 0.02,
    "conclusion": 0.03,
    "discussion": 0.02,
    "experiment": 0.00,
    "results": 0.00,
    "unknown": 0.00,
}


class FaissRecallService(RetrievalService):
    def __init__(
        self,
        repository: FaissRepository,
        embedding_client: DashScopeEmbeddingClient | None = None,
        rerank_client: DashScopeRerankClient | None = None,
    ) -> None:
        self._repository = repository
        self._embedding_client = embedding_client or DashScopeEmbeddingClient()
        self._rerank_client = rerank_client or DashScopeRerankClient()

    @staticmethod
    def _safe_str(value) -> str:
        return "" if value is None else str(value)

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        text = cls._safe_str(text).lower().strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text)
        return text.strip("_")

    @classmethod
    def _canonical_section(cls, section: str) -> str:
        section = cls._safe_str(section).lower()
        if any(keyword in section for keyword in ["abstract", "摘要"]):
            return "abstract"
        if any(keyword in section for keyword in ["introduction", "引言", "绪论"]):
            return "introduction"
        if any(keyword in section for keyword in ["background", "背景"]):
            return "background"
        if any(keyword in section for keyword in ["related work", "related_work", "literature review", "相关工作", "研究现状", "文献综述"]):
            return "related_work"
        if any(keyword in section for keyword in ["method", "methodology", "approach", "framework", "model", "方法", "模型", "框架"]):
            return "method"
        if any(keyword in section for keyword in ["experiment", "evaluation", "实验", "评估"]):
            return "experiment"
        if any(keyword in section for keyword in ["result", "results", "ablation", "结果", "消融"]):
            return "results"
        if any(keyword in section for keyword in ["discussion", "讨论"]):
            return "discussion"
        if any(keyword in section for keyword in ["conclusion", "总结", "结论"]):
            return "conclusion"
        return "unknown"

    def _build_vector_candidates(self, query: str, candidate_k: int) -> list[dict]:
        query_embedding = self._embedding_client.embed_query(query)
        real_k = min(max(candidate_k, 1), self._repository.count())
        if real_k == 0:
            return []
        distances, indices = self._repository.search(query_embedding, real_k)

        candidates: list[dict] = []
        metadata = self._repository.metadata
        for vector_rank, (distance, index) in enumerate(zip(distances[0], indices[0]), start=1):
            if index == -1:
                continue
            item = dict(metadata[index])
            item["paper_id"] = item.get("paper_id") or item.get("source_dir") or self._normalize_text(item.get("title", "")) or "unknown"
            item["vector_distance"] = float(distance)
            item["vector_rank"] = vector_rank
            item["vector_score"] = 1.0 / (1.0 + float(distance))
            item["section_key"] = self._canonical_section(item.get("section", ""))
            item["section_bonus"] = SECTION_BONUS.get(item["section_key"], 0.0)
            candidates.append(item)
        return candidates

    def _score_chunk_candidates(self, query: str, candidates: list[dict]) -> list[dict]:
        docs = [candidate["content"] for candidate in candidates]
        rerank_results = self._rerank_client.rerank(query, docs)
        scored_chunks: list[dict] = []
        for rerank_rank, item in enumerate(rerank_results, start=1):
            chunk = dict(candidates[item["index"]])
            rerank_score = float(item["relevance_score"])
            chunk["chunk_rerank_rank"] = rerank_rank
            chunk["chunk_rerank_score"] = rerank_score
            chunk["chunk_score"] = rerank_score + chunk["section_bonus"]
            scored_chunks.append(chunk)
        scored_chunks.sort(key=lambda entry: entry["chunk_score"], reverse=True)
        return scored_chunks

    @staticmethod
    def _group_chunks_by_paper(scored_chunks: list[dict], per_paper_candidate_limit: int) -> dict[str, list[dict]]:
        paper_groups: defaultdict[str, list[dict]] = defaultdict(list)
        for chunk in scored_chunks:
            if len(paper_groups[chunk["paper_id"]]) < per_paper_candidate_limit:
                paper_groups[chunk["paper_id"]].append(chunk)
        return dict(paper_groups)

    @staticmethod
    def _select_representative_chunks(chunks: list[dict], max_chunks: int = 2) -> list[dict]:
        selected: list[dict] = []
        seen_sections: set[str] = set()
        for chunk in chunks:
            section_key = chunk.get("section_key", "unknown")
            if section_key not in seen_sections:
                selected.append(chunk)
                seen_sections.add(section_key)
            if len(selected) >= max_chunks:
                return selected
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id") or id(chunk)
            selected_ids = {item.get("chunk_id") or id(item) for item in selected}
            if chunk_id not in selected_ids:
                selected.append(chunk)
            if len(selected) >= max_chunks:
                break
        return selected

    @classmethod
    def _build_paper_doc(cls, chunks: list[dict]) -> str:
        head = chunks[0]
        authors = head.get("authors") or []
        author_text = ", ".join(authors[:6]) if isinstance(authors, list) else cls._safe_str(authors)
        blocks = [
            f"Title: {cls._safe_str(head.get('title'))}",
            f"Year: {cls._safe_str(head.get('year'))}",
            f"Venue: {cls._safe_str(head.get('venue'))}",
            f"Authors: {author_text}",
        ]
        for idx, chunk in enumerate(chunks, start=1):
            blocks.append(
                f"[Chunk {idx}]\n"
                f"Section: {cls._safe_str(chunk.get('section'))}\n"
                f"Content: {cls._safe_str(chunk.get('content'))[:500]}"
            )
        return "\n".join(blocks)

    def _build_paper_candidates(self, query: str, paper_groups: dict[str, list[dict]]) -> list[dict]:
        paper_candidates: list[dict] = []
        for paper_id, chunks in paper_groups.items():
            chunks = sorted(chunks, key=lambda item: item["chunk_score"], reverse=True)
            representative_chunks = self._select_representative_chunks(chunks, max_chunks=2)
            top_scores = [chunk["chunk_rerank_score"] for chunk in chunks[:2]]
            pre_score = 0.7 * chunks[0]["chunk_rerank_score"] + 0.2 * float(np.mean(top_scores)) + 0.1 * max(chunk["section_bonus"] for chunk in chunks[:2])
            head = chunks[0]
            paper_candidates.append(
                {
                    "paper_id": paper_id,
                    "title": head.get("title"),
                    "authors": head.get("authors"),
                    "year": head.get("year"),
                    "venue": head.get("venue"),
                    "chunks": chunks,
                    "representative_chunks": representative_chunks,
                    "paper_pre_score": pre_score,
                    "paper_doc": self._build_paper_doc(representative_chunks),
                }
            )

        docs = [paper["paper_doc"] for paper in paper_candidates]
        rerank_results = self._rerank_client.rerank(query, docs)
        for rerank_rank, item in enumerate(rerank_results, start=1):
            paper = paper_candidates[item["index"]]
            rerank_score = float(item["relevance_score"])
            paper["paper_rerank_rank"] = rerank_rank
            paper["paper_rerank_score"] = rerank_score
            paper["paper_score"] = 0.75 * rerank_score + 0.25 * paper["paper_pre_score"]
        for paper in paper_candidates:
            if "paper_score" not in paper:
                paper["paper_rerank_rank"] = 10**9
                paper["paper_rerank_score"] = -1.0
                paper["paper_score"] = paper["paper_pre_score"]
        paper_candidates.sort(key=lambda item: item["paper_score"], reverse=True)
        return paper_candidates

    @staticmethod
    def _select_final_chunks(
        papers: list[dict],
        paper_top_k: int,
        chunk_top_k: int,
        max_chunks_per_paper: int,
    ) -> list[dict]:
        selected_papers = papers[:paper_top_k]
        selected_chunks: list[dict] = []
        paper_chunk_counts: defaultdict[str, int] = defaultdict(int)
        used_chunk_ids: set[str] = set()

        for paper_rank, paper in enumerate(selected_papers, start=1):
            if not paper["chunks"]:
                continue
            chunk = dict(paper["chunks"][0])
            chunk["paper_rank"] = paper_rank
            chunk["paper_score"] = paper["paper_score"]
            chunk["final_score"] = paper["paper_score"] + 0.10 * chunk["chunk_score"]
            selected_chunks.append(chunk)
            paper_chunk_counts[paper["paper_id"]] += 1
            used_chunk_ids.add(chunk.get("chunk_id") or f"{paper['paper_id']}::0")
            if len(selected_chunks) >= chunk_top_k:
                return selected_chunks[:chunk_top_k]

        extra_candidates: list[tuple[str, str, dict]] = []
        for paper_rank, paper in enumerate(selected_papers, start=1):
            main_section = paper["chunks"][0].get("section_key", "unknown") if paper["chunks"] else "unknown"
            for chunk in paper["chunks"][1:]:
                chunk_id = chunk.get("chunk_id") or f"{paper['paper_id']}::{chunk.get('section', '')}::{chunk.get('content', '')[:50]}"
                if chunk_id in used_chunk_ids:
                    continue
                extra = dict(chunk)
                extra["paper_rank"] = paper_rank
                extra["paper_score"] = paper["paper_score"]
                complement_bonus = 0.02 if chunk.get("section_key") != main_section else 0.0
                extra["final_score"] = paper["paper_score"] + 0.10 * chunk["chunk_score"] + complement_bonus
                extra_candidates.append((paper["paper_id"], chunk_id, extra))

        extra_candidates.sort(key=lambda item: item[2]["final_score"], reverse=True)
        for paper_id, chunk_id, chunk in extra_candidates:
            if paper_chunk_counts[paper_id] >= max_chunks_per_paper:
                continue
            selected_chunks.append(chunk)
            paper_chunk_counts[paper_id] += 1
            used_chunk_ids.add(chunk_id)
            if len(selected_chunks) >= chunk_top_k:
                break
        selected_chunks.sort(key=lambda item: (item["paper_rank"], -item["final_score"]))
        return selected_chunks[:chunk_top_k]

    def search(self, query: str, top_k: int = 20) -> list[RetrievedSource]:
        if not self._repository.exists() or self._repository.count() == 0:
            return []
        candidate_k = max(top_k * 4, 80)
        vector_candidates = self._build_vector_candidates(query, candidate_k)
        scored_chunks = self._score_chunk_candidates(query, vector_candidates)
        paper_groups = self._group_chunks_by_paper(scored_chunks, per_paper_candidate_limit=3)
        paper_candidates = self._build_paper_candidates(query, paper_groups)
        final_chunks = self._select_final_chunks(
            papers=paper_candidates,
            paper_top_k=min(top_k, 8, len(paper_candidates)),
            chunk_top_k=top_k,
            max_chunks_per_paper=2,
        )
        return [
            RetrievedSource(
                source_id=item.get("chunk_id", ""),
                paper_id=item.get("paper_id", ""),
                chunk_id=item.get("chunk_id", ""),
                title=str(item.get("title", "") or ""),
                authors=list(item.get("authors", []) or []),
                year=str(item.get("year", "") or ""),
                venue=str(item.get("venue", "") or ""),
                section=str(item.get("section", "") or ""),
                content=str(item.get("content", "") or ""),
                paper_score=item.get("paper_score"),
                chunk_score=item.get("chunk_score"),
            )
            for item in final_chunks
        ]
