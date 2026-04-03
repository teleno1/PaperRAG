from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import numpy as np
import requests
from langchain_openai import ChatOpenAI
from openai import OpenAI

from app.core.config import Settings, get_settings

COMPATIBLE_MODE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MULTIMODAL_EMBEDDING_URL = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding"
RERANK_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
MULTIMODAL_EMBEDDING_MODELS = {
    "qwen3-vl-embedding",
    "multimodal-embedding-v1",
    "tongyi-embedding-vision-plus",
}
VL_RERANK_MODELS = {"qwen3-vl-rerank"}
MULTIMODAL_EMBEDDING_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MULTIMODAL_EMBEDDING_MAX_RETRIES = 2


def _extract_dashscope_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text

    if isinstance(payload, dict):
        if isinstance(payload.get("error"), dict) and payload["error"].get("message"):
            return str(payload["error"]["message"])
        if payload.get("message"):
            return str(payload["message"])
        if payload.get("msg"):
            return str(payload["msg"])
    return response.text


class DashScopeRequestError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class DashScopeEmbeddingClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: OpenAI | None = None

    def _get_api_key(self) -> str:
        api_key = self._settings.models.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY is not configured.")
        return api_key

    def _use_multimodal_endpoint(self) -> bool:
        return self._settings.models.embedding_model in MULTIMODAL_EMBEDDING_MODELS

    def _get_embedding_dimension(self) -> int | None:
        return self._settings.models.embedding_dimension

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self._get_api_key(),
                base_url=COMPATIBLE_MODE_BASE_URL,
            )
        return self._client

    def _embed_texts_compatible(self, texts: list[str]) -> list[list[float]]:
        client = self._ensure_client()
        request_kwargs: dict[str, Any] = {
            "model": self._settings.models.embedding_model,
            "input": texts,
        }
        dimension = self._get_embedding_dimension()
        if dimension is not None:
            request_kwargs["dimensions"] = dimension
        response = client.embeddings.create(**request_kwargs)
        return [item.embedding for item in response.data]

    def _embed_texts_multimodal(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts_multimodal_with_fallback(texts)

    def _embed_texts_multimodal_with_fallback(self, texts: list[str]) -> list[list[float]]:
        last_error: DashScopeRequestError | None = None
        for attempt in range(MULTIMODAL_EMBEDDING_MAX_RETRIES + 1):
            try:
                return self._request_multimodal_embeddings(texts)
            except DashScopeRequestError as exc:
                last_error = exc
                if exc.status_code not in MULTIMODAL_EMBEDDING_RETRYABLE_STATUS_CODES:
                    raise
                if attempt < MULTIMODAL_EMBEDDING_MAX_RETRIES:
                    time.sleep(0.5 * (attempt + 1))

        if len(texts) > 1 and last_error and last_error.status_code in MULTIMODAL_EMBEDDING_RETRYABLE_STATUS_CODES:
            midpoint = max(1, len(texts) // 2)
            left_embeddings = self._embed_texts_multimodal_with_fallback(texts[:midpoint])
            right_embeddings = self._embed_texts_multimodal_with_fallback(texts[midpoint:])
            return left_embeddings + right_embeddings

        if last_error is not None:
            raise last_error
        raise RuntimeError("DashScope multimodal embedding request failed without an error response.")

    def _request_multimodal_embeddings(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            MULTIMODAL_EMBEDDING_URL,
            headers={
                "Authorization": f"Bearer {self._get_api_key()}",
                "Content-Type": "application/json",
            },
            json=self._build_multimodal_embedding_payload(texts),
            timeout=60,
        )
        if response.status_code != 200:
            raise DashScopeRequestError(
                f"DashScope multimodal embedding request failed: {_extract_dashscope_error(response)}",
                status_code=response.status_code,
            )
        payload = response.json()
        embeddings = payload.get("output", {}).get("embeddings", [])
        vectors = [item["embedding"] for item in embeddings]
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"DashScope multimodal embedding returned {len(vectors)} vectors for {len(texts)} inputs."
            )
        return vectors

    def _build_multimodal_embedding_payload(self, texts: list[str]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._settings.models.embedding_model,
            "input": {
                "contents": [{"text": text} for text in texts],
            },
        }
        dimension = self._get_embedding_dimension()
        if dimension is not None:
            payload["parameters"] = {"dimension": dimension}
        return payload

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._use_multimodal_endpoint():
            return self._embed_texts_multimodal(texts)
        return self._embed_texts_compatible(texts)

    def embed_query(self, query: str) -> np.ndarray:
        embedding = self.embed_texts([query])[0]
        return np.array(embedding).astype("float32").reshape(1, -1)


class DashScopeRerankClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _get_api_key(self) -> str:
        return self._settings.models.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")

    def _build_rerank_input(self, query: str, docs: list[str]) -> dict[str, Any]:
        if self._settings.models.rerank_model in VL_RERANK_MODELS:
            return {
                "query": {"text": query},
                "documents": [{"text": doc} for doc in docs],
            }
        return {"query": query, "documents": docs}

    def rerank(self, query: str, docs: list[str]) -> list[dict[str, Any]]:
        if not docs:
            return []

        api_key = self._get_api_key()
        if not api_key:
            return [{"index": idx, "relevance_score": float(len(docs) - idx)} for idx in range(len(docs))]

        response = requests.post(
            RERANK_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._settings.models.rerank_model,
                "input": self._build_rerank_input(query, docs),
            },
            timeout=60,
        )
        if response.status_code != 200:
            return [{"index": idx, "relevance_score": float(len(docs) - idx)} for idx in range(len(docs))]

        results = response.json()["output"]["results"]
        return sorted(results, key=lambda item: item["relevance_score"], reverse=True)


class DeepSeekJsonClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: OpenAI | None = None

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            api_key = self._settings.models.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", "")
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY is not configured.")
            base_url = self._settings.models.deepseek_base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def complete_json(
        self,
        prompt: str,
        temperature: float = 0.2,
        system_prompt: str | None = None,
    ) -> Any:
        client = self._ensure_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=self._settings.models.llm_model,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content or ""
        return self._parse_json_content(content)

    @staticmethod
    def _parse_json_content(content: str) -> Any:
        text = content.strip()
        if not text:
            raise ValueError("LLM returned empty content.")

        candidates = [text]

        fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        candidates.extend(block.strip() for block in fenced_blocks if block.strip())

        first_object = text.find("{")
        last_object = text.rfind("}")
        if first_object != -1 and last_object != -1 and last_object > first_object:
            candidates.append(text[first_object : last_object + 1].strip())

        first_array = text.find("[")
        last_array = text.rfind("]")
        if first_array != -1 and last_array != -1 and last_array > first_array:
            candidates.append(text[first_array : last_array + 1].strip())

        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        snippet = text[:300].replace("\n", "\\n")
        raise ValueError(f"Failed to parse JSON from LLM response: {snippet}")


class DeepSeekChatFactory:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def create(self, temperature: float) -> ChatOpenAI:
        api_key = self._settings.models.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured.")
        base_url = self._settings.models.deepseek_base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        return ChatOpenAI(
            model=self._settings.models.llm_model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )
