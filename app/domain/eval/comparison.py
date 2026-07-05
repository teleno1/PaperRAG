from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.eval.results import EvalRunMetrics

ChunkingPreset = Literal["balanced", "fine_grained"]
RerankMode = Literal["on", "off"]


class StrategyConfig(BaseModel):
    strategy_id: str
    chunking_preset: ChunkingPreset
    top_k: int
    rerank_mode: RerankMode


class StrategyComparisonRow(BaseModel):
    strategy_id: str
    chunking_preset: ChunkingPreset
    top_k: int
    rerank_mode: RerankMode
    run_dir: Path
    case_count: int
    failure_count: int
    metrics: EvalRunMetrics


class StrategyComparisonResult(BaseModel):
    run_id: str
    run_dir: Path
    dataset_path: Path
    source_dir: Path
    comparison_path: Path
    summary_table: str
    strategies: list[StrategyComparisonRow] = Field(default_factory=list)
