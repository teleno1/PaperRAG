from __future__ import annotations

import json

from app.core.config import get_settings
from app.core.exceptions import PaperRAGError, RetrievalError
from app.core.paths import PathManager, get_paths
from app.domain.citation.source_validation import validate_cited_source_ids
from app.domain.report.models import GeneratedReport, ReportRequest, ReportResult
from app.domain.report.prompts import build_report_prompts
from app.domain.report.renderer import render_report_content
from app.infrastructure.llm.clients import DeepSeekJsonClient
from app.use_cases._shared import build_retrieval_service, build_run_id


def _output_filename(output_format: str) -> str:
    if output_format == "json":
        return "report.json"
    if output_format == "bullet_summary":
        return "report.bullet_summary.md"
    return "report.md"


def _coerce_section_payload(section: object) -> dict | None:
    if not isinstance(section, dict):
        return None

    title = str(section.get("title") or "Details").strip()
    body = str(
        section.get("body")
        or section.get("detail")
        or section.get("details")
        or section.get("summary")
        or ""
    ).strip()
    cited_source_ids = section.get("cited_source_ids", []) or []
    if not isinstance(cited_source_ids, list):
        cited_source_ids = []
    return {
        "title": title,
        "body": body,
        "cited_source_ids": [str(item).strip() for item in cited_source_ids if str(item).strip()],
    }


def _coerce_generated_report_payload(raw_payload: object, query: str) -> object:
    if not isinstance(raw_payload, dict):
        return raw_payload

    if "title" in raw_payload and "sections" in raw_payload:
        return raw_payload

    summary = str(raw_payload.get("summary") or raw_payload.get("overview") or "").strip()
    details = raw_payload.get("details")
    sections: list[dict] = []

    if isinstance(details, list):
        for item in details:
            section_payload = _coerce_section_payload(item)
            if section_payload is not None:
                sections.append(section_payload)
    elif isinstance(details, dict):
        section_payload = _coerce_section_payload(details)
        if section_payload is not None:
            sections.append(section_payload)
    elif details is not None:
        detail_text = str(details).strip()
        if detail_text:
            sections.append(
                {
                    "title": "Details",
                    "body": detail_text,
                    "cited_source_ids": [],
                }
            )

    if summary or sections:
        return {
            "title": f"Report: {query[:80]}".strip(),
            "overview": summary,
            "sections": sections,
        }

    return raw_payload


class RunReportUseCase:
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
        output_format: str = "markdown",
        top_k: int | None = None,
        run_id: str | None = None,
    ) -> ReportResult:
        request = ReportRequest(
            query=query,
            output_format=output_format,
            top_k=top_k or max(get_settings().pipeline.top_k_recall, 1),
        )
        try:
            retrieved_sources = self._retrieval.search(query=request.query, top_k=request.top_k)
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError(query=request.query, reason=str(exc)) from exc

        if not retrieved_sources:
            report = GeneratedReport(
                title=f"Report: {request.query}",
                overview="No supporting sources were retrieved for the request.",
                sections=[],
            )
        else:
            system_prompt, prompt = build_report_prompts(request.query, retrieved_sources)
            try:
                raw_payload = self._llm.complete_json(
                    prompt=prompt,
                    temperature=get_settings().pipeline.temperature_chapter,
                    system_prompt=system_prompt,
                )
                report = GeneratedReport.model_validate(_coerce_generated_report_payload(raw_payload, request.query))
            except Exception as exc:
                raise PaperRAGError(
                    "Report generation failed.",
                    {"query": request.query, "reason": str(exc)},
                ) from exc

        validation = validate_cited_source_ids(report.all_cited_source_ids(), retrieved_sources)
        report = report.sanitized(set(validation.available_source_ids))

        run_id = run_id or build_run_id()
        run_dir = self._paths.outputs_dir / "reports" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        report_json_path = run_dir / "report.json"
        output_path = run_dir / _output_filename(request.output_format)
        retrieved_sources_path = run_dir / "retrieved_sources.json"
        validation_path = run_dir / "validation.json"

        report_json_path.write_text(report.to_pretty_json(), encoding="utf-8")
        output_path.write_text(render_report_content(report, request.output_format), encoding="utf-8")
        retrieved_sources_path.write_text(
            json.dumps([source.model_dump() for source in retrieved_sources], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        validation_path.write_text(
            json.dumps(validation.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return ReportResult(
            run_id=run_id,
            run_dir=run_dir,
            query=request.query,
            output_format=request.output_format,
            output_path=output_path,
            report_json_path=report_json_path,
            retrieved_sources_path=retrieved_sources_path,
            validation_path=validation_path,
            content=output_path.read_text(encoding="utf-8"),
            report=report,
            retrieved_sources=retrieved_sources,
            validation=validation,
        )
