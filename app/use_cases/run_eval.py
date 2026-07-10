from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path
from typing import Callable

from app.core.exceptions import PaperRAGError
from app.core.paths import PathManager, get_paths
from app.domain.eval import (
    EvalCaseResult,
    EvalRunMetrics,
    EvalRunResult,
    GenerationCaseMetrics,
    RetrievalCaseMetrics,
    aggregate_generation_metrics,
    aggregate_retrieval_metrics,
    build_generation_case_metrics,
    build_retrieval_case_metrics,
    load_eval_dataset,
)
from app.domain.report.models import ReportResult
from app.domain.retrieval.models import RetrievedSource
from app.use_cases._shared import build_run_id
from app.use_cases.run_report import RunReportUseCase


def _normalize_eval_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return normalized or "case"


def _retrieval_metric_ids(
    retrieved_sources: list[RetrievedSource],
    expected_source_ids: list[str],
) -> list[str]:
    expected = {str(value).strip() for value in expected_source_ids if str(value).strip()}
    if any(str(source.source_id).strip() in expected for source in retrieved_sources):
        return [str(source.source_id).strip() for source in retrieved_sources if str(source.source_id).strip()]
    if any(str(source.document_id or source.paper_id).strip() in expected for source in retrieved_sources):
        return [
            str(source.document_id or source.paper_id).strip()
            for source in retrieved_sources
            if str(source.document_id or source.paper_id).strip()
        ]
    return [
        str(source.document_id or source.paper_id or source.source_id).strip()
        for source in retrieved_sources
        if str(source.document_id or source.paper_id or source.source_id).strip()
    ]


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[94]


class RunEvalUseCase:
    def __init__(
        self,
        dataset_loader=load_eval_dataset,
        report_use_case: RunReportUseCase | None = None,
        paths: PathManager | None = None,
        timer: Callable[[], float] | None = None,
    ) -> None:
        self._dataset_loader = dataset_loader
        self._report_use_case = report_use_case
        self._paths = paths or get_paths()
        self._timer = timer or time.perf_counter

    def _build_case_paths(self, run_dir: Path) -> PathManager:
        settings = getattr(self._paths, "_settings").model_copy(deep=True)
        settings.paths.outputs_dir = str(run_dir / "case_outputs")
        settings.paths.eval_outputs_dir = str(self._paths.eval_outputs_dir)
        return PathManager(settings_override=settings)

    def _get_report_use_case(self, run_dir: Path) -> RunReportUseCase:
        if self._report_use_case is not None:
            return self._report_use_case
        return RunReportUseCase(paths=self._build_case_paths(run_dir))

    @staticmethod
    def _classify_failure_label(
        *,
        answer_expectation: str,
        retrieval_metrics: RetrievalCaseMetrics,
        generation_metrics: GenerationCaseMetrics,
        error: str | None,
    ) -> str | None:
        if error is not None:
            return "runtime_error"
        if generation_metrics.unknown_citation_count > 0:
            return "citation_registry_failure"
        if generation_metrics.format_compliance < 1.0:
            return "format_failure"
        if generation_metrics.unsupported_aspect_violation_count > 0:
            return "unsupported_assertion"
        if answer_expectation == "full_answer":
            if retrieval_metrics.recall_at_5 < 1.0:
                return "retrieval_miss"
            if generation_metrics.answer_point_coverage < 0.8:
                return "full_answer_failure"
            return None
        if answer_expectation == "partial_answer":
            if generation_metrics.answer_point_coverage <= 0.0 or not generation_metrics.abstention_cue_present:
                return "partial_answer_failure"
            return None
        if not generation_metrics.abstention_cue_present:
            return "abstention_failure"
        return None

    @classmethod
    def _case_passed(cls, case_result: EvalCaseResult) -> bool:
        return (
            cls._classify_failure_label(
                answer_expectation=case_result.answer_expectation,
                retrieval_metrics=case_result.retrieval_metrics,
                generation_metrics=case_result.generation_metrics,
                error=case_result.error,
            )
            is None
        )

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict]) -> None:
        path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )

    @staticmethod
    def _build_case_result(row, report_result: ReportResult, latency_ms: float) -> EvalCaseResult:
        retrieval_metric_ids = _retrieval_metric_ids(
            report_result.retrieved_sources,
            row.expected_sources,
        )
        retrieved_source_ids = [
            str(source.source_id).strip()
            for source in report_result.retrieved_sources
            if str(source.source_id).strip()
        ]
        cited_source_ids = report_result.report.all_cited_source_ids()
        retrieval_metrics = build_retrieval_case_metrics(
            retrieved_source_ids=retrieval_metric_ids,
            expected_source_ids=row.expected_sources,
        )
        generation_metrics = build_generation_case_metrics(
            cited_source_ids=cited_source_ids,
            expected_source_ids=row.expected_sources,
            retrieved_source_ids=retrieved_source_ids,
            output_content=report_result.content,
            output_format=row.output_format,
            answer_points=row.answer_points,
            unsupported_aspects=row.unsupported_aspects,
        )
        return EvalCaseResult(
            case_id=row.id,
            query=row.query,
            answer_expectation=row.answer_expectation,
            question_shape=row.question_shape,
            expected_source_ids=row.expected_sources,
            answer_points=row.answer_points,
            unsupported_aspects=row.unsupported_aspects,
            retrieved_source_ids=retrieved_source_ids,
            cited_source_ids=cited_source_ids,
            output_format=row.output_format,
            report_run_id=report_result.run_id,
            output_path=str(report_result.output_path),
            latency_ms=latency_ms,
            retrieval_metrics=retrieval_metrics,
            generation_metrics=generation_metrics,
        )

    @staticmethod
    def _build_failure_result(row, latency_ms: float, error: str) -> EvalCaseResult:
        retrieval_metrics = build_retrieval_case_metrics(
            retrieved_source_ids=[],
            expected_source_ids=row.expected_sources,
        )
        generation_metrics = build_generation_case_metrics(
            cited_source_ids=[],
            expected_source_ids=row.expected_sources,
            retrieved_source_ids=[],
            output_content="",
            output_format=row.output_format,
            answer_points=row.answer_points,
            unsupported_aspects=row.unsupported_aspects,
        )
        return EvalCaseResult(
            case_id=row.id,
            query=row.query,
            answer_expectation=row.answer_expectation,
            question_shape=row.question_shape,
            expected_source_ids=row.expected_sources,
            answer_points=row.answer_points,
            unsupported_aspects=row.unsupported_aspects,
            retrieved_source_ids=[],
            cited_source_ids=[],
            output_format=row.output_format,
            latency_ms=latency_ms,
            error=error,
            retrieval_metrics=retrieval_metrics,
            generation_metrics=generation_metrics,
        )

    def execute(
        self,
        dataset: str | Path,
        top_k: int | None = None,
        run_id: str | None = None,
    ) -> EvalRunResult:
        run_id = run_id or build_run_id()
        run_dir = self._paths.get_eval_output_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        dataset_path = Path(dataset)
        try:
            eval_dataset = self._dataset_loader(dataset_path)
            report_use_case = self._get_report_use_case(run_dir)
        except PaperRAGError:
            raise
        except Exception as exc:
            raise PaperRAGError(
                "Evaluation setup failed.",
                {"dataset_path": str(dataset_path), "reason": str(exc)},
            ) from exc

        case_results: list[EvalCaseResult] = []
        retrieval_debug_rows: list[dict] = []
        latencies: list[float] = []

        for row in eval_dataset.rows:
            case_run_id = f"case-{_normalize_eval_id(row.id)}"
            start_time = self._timer()
            retrieved_source_records: list[dict] = []
            retrieval_metric_ids: list[str] = []
            try:
                report_result = report_use_case.execute(
                    query=row.query,
                    output_format=row.output_format,
                    top_k=top_k,
                    run_id=case_run_id,
                )
                latency_ms = (self._timer() - start_time) * 1000
                retrieved_source_records = [
                    source.model_dump(mode="json") for source in report_result.retrieved_sources
                ]
                retrieval_metric_ids = _retrieval_metric_ids(
                    report_result.retrieved_sources,
                    row.expected_sources,
                )
                case_result = self._build_case_result(row=row, report_result=report_result, latency_ms=latency_ms)
            except Exception as exc:
                latency_ms = (self._timer() - start_time) * 1000
                case_result = self._build_failure_result(row=row, latency_ms=latency_ms, error=str(exc))

            latencies.append(latency_ms)
            case_result.failure_label = self._classify_failure_label(
                answer_expectation=case_result.answer_expectation,
                retrieval_metrics=case_result.retrieval_metrics,
                generation_metrics=case_result.generation_metrics,
                error=case_result.error,
            )
            case_result.passed = self._case_passed(case_result)
            case_results.append(case_result)
            retrieval_debug_rows.append(
                {
                    "case_id": case_result.case_id,
                    "query": case_result.query,
                    "expected_source_ids": case_result.expected_source_ids,
                    "retrieved_source_ids": case_result.retrieved_source_ids,
                    "retrieval_metric_ids": retrieval_metric_ids,
                    "retrieved_sources": retrieved_source_records,
                    "cited_source_ids": case_result.cited_source_ids,
                    "retrieval_metrics": case_result.retrieval_metrics.model_dump(mode="json"),
                    "report_run_id": case_result.report_run_id,
                    "error": case_result.error,
                }
            )

        retrieval_metrics = aggregate_retrieval_metrics([case.retrieval_metrics for case in case_results])
        generation_metrics = aggregate_generation_metrics([case.generation_metrics for case in case_results])
        failure_count = sum(1 for case in case_results if not case.passed)
        metrics = EvalRunMetrics(
            retrieval=retrieval_metrics,
            generation=generation_metrics,
            avg_latency_ms=(sum(latencies) / len(latencies)) if latencies else 0.0,
            p95_latency_ms=_p95(latencies),
            failure_rate=(failure_count / len(case_results)) if case_results else 0.0,
        )

        metrics_path = run_dir / "metrics.json"
        cases_path = run_dir / "cases.jsonl"
        failures_path = run_dir / "failures.jsonl"
        retrieval_debug_path = run_dir / "retrieval_debug.jsonl"

        metrics_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "dataset_path": str(dataset_path),
                    "case_count": len(case_results),
                    "failure_count": failure_count,
                    "metrics": metrics.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._write_jsonl(cases_path, [case.model_dump(mode="json") for case in case_results])
        self._write_jsonl(failures_path, [case.model_dump(mode="json") for case in case_results if not case.passed])
        self._write_jsonl(retrieval_debug_path, retrieval_debug_rows)

        return EvalRunResult(
            run_id=run_id,
            run_dir=run_dir,
            dataset_path=dataset_path,
            case_count=len(case_results),
            failure_count=failure_count,
            metrics_path=metrics_path,
            cases_path=cases_path,
            failures_path=failures_path,
            retrieval_debug_path=retrieval_debug_path,
            metrics=metrics,
            cases=case_results,
        )
