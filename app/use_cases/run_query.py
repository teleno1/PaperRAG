from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import PaperRAGError, RetrievalError
from app.core.paths import PathManager, get_paths
from app.domain.answer.models import AnswerRequest, AnswerResult, CitedAnswerDraft
from app.domain.answer.prompts import build_cited_answer_prompts
from app.domain.citation.source_validation import validate_cited_source_ids
from app.domain.retrieval.models import RetrievedSource
from app.infrastructure.llm.clients import DeepSeekJsonClient
from app.use_cases._shared import build_retrieval_service


def _trace_only_sources(retrieved_sources: list[RetrievedSource]) -> list[RetrievedSource]:
    return [
        source.model_copy(
            update={
                "content": "",
            }
        )
        for source in retrieved_sources
    ]


class RunQueryUseCase:
    def __init__(
        self,
        retrieval_service=None,
        llm_client: DeepSeekJsonClient | None = None,
        paths: PathManager | None = None,
    ) -> None:
        self._paths = paths or get_paths()
        self._retrieval = retrieval_service or build_retrieval_service(paths=self._paths)
        self._llm = llm_client or DeepSeekJsonClient()

    def execute(
        self,
        query: str,
        top_k: int | None = None,
        include_retrieved_sources: bool = True,
    ) -> AnswerResult:
        request = AnswerRequest(
            query=query,
            top_k=top_k or max(get_settings().pipeline.top_k_recall, 1),
            include_retrieved_sources=include_retrieved_sources,
        )
        try:
            retrieved_sources = self._retrieval.search(query=request.query, top_k=request.top_k)
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError(query=request.query, reason=str(exc)) from exc

        if not retrieved_sources:
            validation = validate_cited_source_ids([], [])
            return AnswerResult(
                query=request.query,
                answer_text="No supporting sources were retrieved for the query.",
                cited_source_ids=[],
                retrieved_sources=[],
                validation=validation,
            )

        system_prompt, prompt = build_cited_answer_prompts(request.query, retrieved_sources)
        try:
            raw_payload = self._llm.complete_json(
                prompt=prompt,
                temperature=get_settings().pipeline.temperature_chapter,
                system_prompt=system_prompt,
            )
            draft = CitedAnswerDraft.model_validate(raw_payload)
        except Exception as exc:
            raise PaperRAGError(
                "Cited answer generation failed.",
                {"query": request.query, "reason": str(exc)},
            ) from exc

        validation = validate_cited_source_ids(draft.cited_source_ids, retrieved_sources)
        return AnswerResult(
            query=request.query,
            answer_text=draft.answer_text,
            cited_source_ids=validation.cited_source_ids,
            retrieved_sources=retrieved_sources if request.include_retrieved_sources else _trace_only_sources(retrieved_sources),
            validation=validation,
        )
