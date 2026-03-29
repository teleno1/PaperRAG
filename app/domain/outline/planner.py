from __future__ import annotations

from collections import defaultdict

from app.core.config import get_settings
from app.domain.retrieval.service import RetrievalService
from app.domain.review.models import RetrievedSource
from app.infrastructure.llm.clients import DeepSeekJsonClient


class OutlinePlanner:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_client: DeepSeekJsonClient | None = None,
    ) -> None:
        self._retrieval = retrieval_service
        self._llm = llm_client or DeepSeekJsonClient()
        self._settings = get_settings()

    def expand_queries(self, user_query: str) -> list[str]:
        query_count = max(self._settings.pipeline.outline_query_count, 1)
        prompt = f"""
你是一个学术检索助手。

用户研究主题：
{user_query}

请从不同角度扩展出 {query_count} 组检索 query。
优先覆盖：方法、应用、研究现状、问题挑战、发展趋势。

要求：
- 尽量同时包含中文和英文表达，便于召回。
- 避免重复表达。
- 只输出 JSON 数组。
"""
        result = self._llm.complete_json(prompt=prompt, temperature=0.7)
        if isinstance(result, list):
            queries = [str(item).strip() for item in result if str(item).strip()]
            if queries:
                return queries
        return [user_query]

    def retrieve_chunks(
        self,
        queries: list[str],
        total_chunk_limit: int | None = None,
        max_chunks_per_paper: int = 1,
    ) -> list[RetrievedSource]:
        total_chunk_limit = max(total_chunk_limit or self._settings.pipeline.top_k_recall, 1)
        all_chunks: list[RetrievedSource] = []
        for query in queries:
            all_chunks.extend(self._retrieval.search(query=query, top_k=total_chunk_limit))

        unique: list[RetrievedSource] = []
        seen_chunk_ids: set[str] = set()
        for chunk in all_chunks:
            if chunk.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk.chunk_id)
            unique.append(chunk)

        paper_counter: defaultdict[str, int] = defaultdict(int)
        ordered = sorted(
            unique,
            key=lambda item: (
                item.paper_score or 0.0,
                item.chunk_score or 0.0,
            ),
            reverse=True,
        )
        limited: list[RetrievedSource] = []
        for chunk in ordered:
            if paper_counter[chunk.paper_id] >= max_chunks_per_paper:
                continue
            limited.append(chunk)
            paper_counter[chunk.paper_id] += 1
            if len(limited) >= total_chunk_limit:
                break
        return limited

    def build_context(self, chunks: list[RetrievedSource]) -> str:
        blocks: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"[Paper {idx}]",
                        f"Title: {chunk.title}",
                        f"Authors: {', '.join(chunk.authors[:6])}",
                        f"Year: {chunk.year}",
                        f"Venue: {chunk.venue}",
                        f"Section: {chunk.section}",
                        f"Content: {chunk.content[:300]}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def generate_outline(self, user_query: str, chunks: list[RetrievedSource]) -> dict:
        context = self.build_context(chunks)
        prompt = f"""
你是一位学术综述论文大纲生成专家。
你的任务是根据研究主题和参考文献片段，输出一个用于撰写综述论文的层级化大纲。
你必须且只能输出一个合法 JSON 对象。

输出结构：
{{
  "language": "中文或 English",
  "title": "综述题目",
  "sections": [
    {{
      "title": "章节标题",
      "description": "章节说明",
      "query": "用于检索的查询词，若无需检索则为空字符串",
      "needs_retrieval": true,
      "write_stage": "body 或 final_pass",
      "citation_policy": "required / optional / none",
      "subsections": []
    }}
  ]
}}

硬性要求：
- 必须包含“摘要”章节，且其 query 为空、needs_retrieval 为 false、write_stage 为 final_pass、citation_policy 为 none。
- 必须包含“研究背景与意义”“国内外研究现状”“目前存在的问题”这三类正文章节。
- 必须包含“结语”或“总结与展望”章节，且其 query 为空、needs_retrieval 为 false、write_stage 为 final_pass、citation_policy 为 none。
- 正文章节默认 write_stage 为 body，citation_policy 为 required，并给出可执行的 query。
- 只输出 JSON。

研究主题：
{user_query}

参考文献片段：
{context}
"""
        result = self._llm.complete_json(prompt=prompt, temperature=0.2)
        if not isinstance(result, dict):
            raise ValueError("Outline generation did not return a JSON object.")
        return result

    def plan(self, user_query: str) -> dict:
        queries = self.expand_queries(user_query)
        chunks = self.retrieve_chunks(queries)
        return self.generate_outline(user_query, chunks)
