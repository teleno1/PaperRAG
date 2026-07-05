from __future__ import annotations

import json
from pathlib import Path

from app.core.exceptions import PaperRAGError
from app.core.paths import PathManager, get_paths
from app.domain.eval import StrategyComparisonResult, StrategyComparisonRow, StrategyConfig
from app.infrastructure.chunking.chunk_builder import ChunkBuilder
from app.infrastructure.retrieval.faiss_recall_service import FaissRecallService
from app.infrastructure.vectorstore.faiss_repository import FaissRepository
from app.infrastructure.vectorstore.index_builder import IndexBuilder
from app.use_cases._shared import build_run_id
from app.use_cases.run_eval import RunEvalUseCase
from app.use_cases.run_report import RunReportUseCase

DEFAULT_COMPARISON_SOURCE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "samples" / "phase2_corpus"

def build_chunk_builder_for_preset(preset: str) -> ChunkBuilder:
    if preset == "fine_grained":
        return ChunkBuilder(max_tokens=250, overlap_sentences=1, min_unit_len=30)
    return ChunkBuilder(max_tokens=500, overlap_sentences=2, min_unit_len=50)


def build_default_strategy_configs() -> list[StrategyConfig]:
    configs: list[StrategyConfig] = []
    for chunking_preset in ["balanced", "fine_grained"]:
        for top_k in [3, 5]:
            for rerank_mode in ["on", "off"]:
                configs.append(
                    StrategyConfig(
                        strategy_id=f"{chunking_preset}_topk{top_k}_rerank_{rerank_mode}",
                        chunking_preset=chunking_preset,
                        top_k=top_k,
                        rerank_mode=rerank_mode,
                    )
                )
    return configs


def _format_summary_table(rows: list[StrategyComparisonRow]) -> str:
    header = "strategy_id | chunking | top_k | rerank | recall@5 | mrr | citation_hit_rate | failure_rate"
    separator = "--- | --- | --- | --- | --- | --- | --- | ---"
    body = [
        (
            f"{row.strategy_id} | {row.chunking_preset} | {row.top_k} | {row.rerank_mode} | "
            f"{row.metrics.retrieval.recall_at_5:.2f} | {row.metrics.retrieval.mrr:.2f} | "
            f"{row.metrics.generation.citation_hit_rate:.2f} | {row.metrics.failure_rate:.2f}"
        )
        for row in rows
    ]
    return "\n".join([header, separator, *body])


class RunEvalStrategyComparisonUseCase:
    def __init__(
        self,
        *,
        paths: PathManager | None = None,
        strategy_runner=None,
    ) -> None:
        self._paths = paths or get_paths()
        self._strategy_runner = strategy_runner

    def _build_strategy_paths(self, comparison_root: Path) -> PathManager:
        settings = getattr(self._paths, "_settings").model_copy(deep=True)
        settings.paths.eval_outputs_dir = str(comparison_root / "strategies")
        return PathManager(settings_override=settings)

    def _build_report_paths(self, comparison_root: Path, strategy_id: str) -> PathManager:
        settings = getattr(self._paths, "_settings").model_copy(deep=True)
        settings.paths.outputs_dir = str(comparison_root / "strategies" / strategy_id / "case_outputs")
        return PathManager(settings_override=settings)

    def _build_strategy_report_use_case(
        self,
        *,
        comparison_root: Path,
        strategy: StrategyConfig,
        source_dir: Path,
    ) -> RunReportUseCase:
        strategy_dir = comparison_root / "strategies" / strategy.strategy_id
        repository = FaissRepository(
            index_path=strategy_dir / "database" / "paper_index.faiss",
            metadata_path=strategy_dir / "database" / "metadata.json",
        )
        index_builder = IndexBuilder(
            chunk_builder=build_chunk_builder_for_preset(strategy.chunking_preset),
        )
        vectors, metadata = index_builder.build_from_source_dir(source_dir)
        repository.save(vectors, metadata)
        retrieval_service = FaissRecallService(
            repository=repository,
            enable_rerank=(strategy.rerank_mode == "on"),
        )
        return RunReportUseCase(
            retrieval_service=retrieval_service,
            paths=self._build_report_paths(comparison_root, strategy.strategy_id),
        )

    def _run_strategy(
        self,
        *,
        dataset: str | Path,
        comparison_root: Path,
        source_dir: Path,
        strategy: StrategyConfig,
    ):
        if self._strategy_runner is not None:
            return self._strategy_runner(
                dataset=dataset,
                comparison_root=comparison_root,
                source_dir=source_dir,
                strategy=strategy,
            )

        strategy_paths = self._build_strategy_paths(comparison_root)
        report_use_case = self._build_strategy_report_use_case(
            comparison_root=comparison_root,
            strategy=strategy,
            source_dir=source_dir,
        )
        eval_use_case = RunEvalUseCase(
            report_use_case=report_use_case,
            paths=strategy_paths,
        )
        return eval_use_case.execute(
            dataset=dataset,
            top_k=strategy.top_k,
            run_id=strategy.strategy_id,
        )

    def execute(
        self,
        *,
        dataset: str | Path,
        source_dir: str | Path = DEFAULT_COMPARISON_SOURCE_DIR,
        run_id: str | None = None,
        strategy_configs: list[StrategyConfig] | None = None,
    ) -> StrategyComparisonResult:
        run_id = run_id or build_run_id()
        comparison_root = self._paths.get_eval_output_dir(run_id)
        comparison_root.mkdir(parents=True, exist_ok=True)

        dataset_path = Path(dataset)
        source_dir_path = Path(source_dir)
        if not source_dir_path.exists():
            raise PaperRAGError(
                "Strategy comparison source directory does not exist.",
                {"source_dir": str(source_dir_path)},
            )
        rows: list[StrategyComparisonRow] = []
        try:
            for strategy in strategy_configs or build_default_strategy_configs():
                result = self._run_strategy(
                    dataset=dataset_path,
                    comparison_root=comparison_root,
                    source_dir=source_dir_path,
                    strategy=strategy,
                )
                rows.append(
                    StrategyComparisonRow(
                        strategy_id=strategy.strategy_id,
                        chunking_preset=strategy.chunking_preset,
                        top_k=strategy.top_k,
                        rerank_mode=strategy.rerank_mode,
                        run_dir=result.run_dir,
                        case_count=result.case_count,
                        failure_count=result.failure_count,
                        metrics=result.metrics,
                    )
                )
        except PaperRAGError:
            raise
        except Exception as exc:
            raise PaperRAGError(
                "Strategy comparison failed.",
                {"dataset_path": str(dataset_path), "source_dir": str(source_dir_path), "reason": str(exc)},
            ) from exc

        summary_table = _format_summary_table(rows)
        comparison_path = comparison_root / "comparison.json"
        comparison_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "dataset_path": str(dataset_path),
                    "source_dir": str(source_dir_path),
                    "summary_table": summary_table,
                    "strategies": [row.model_dump(mode="json") for row in rows],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return StrategyComparisonResult(
            run_id=run_id,
            run_dir=comparison_root,
            dataset_path=dataset_path,
            source_dir=source_dir_path,
            comparison_path=comparison_path,
            summary_table=summary_table,
            strategies=rows,
        )
