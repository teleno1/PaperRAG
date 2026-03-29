"""统一日志模块。"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.paths import get_paths


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """设置日志。

    Args:
        level: 日志级别
        log_file: 日志文件路径（可选）
        format_string: 日志格式字符串

    Returns:
        配置好的logger
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # 根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有handlers
    root_logger.handlers.clear()

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件handler（可选）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取logger实例。

    Args:
        name: logger名称

    Returns:
        Logger实例
    """
    return logging.getLogger(name)


class PipelineLogger:
    """流水线日志记录器，记录阶段、路径、耗时等信息。"""

    def __init__(self, name: str = "pipeline"):
        self.logger = get_logger(name)
        self._stage_start: Optional[datetime] = None
        self._current_stage: Optional[str] = None

    def start_stage(self, stage: str) -> None:
        """开始一个阶段。"""
        self._current_stage = stage
        self._stage_start = datetime.now()
        self.logger.info(f"========== 开始阶段: {stage} ==========")

    def end_stage(self, success: bool = True) -> float:
        """结束当前阶段。

        Returns:
            阶段耗时（秒）
        """
        if self._stage_start is None:
            return 0.0

        elapsed = (datetime.now() - self._stage_start).total_seconds()
        status = "成功" if success else "失败"
        self.logger.info(
            f"========== 阶段 {self._current_stage} {status}，耗时 {elapsed:.2f}s =========="
        )
        self._stage_start = None
        self._current_stage = None
        return elapsed

    def log_input(self, path: Path) -> None:
        """记录输入路径。"""
        self.logger.info(f"输入: {path}")

    def log_output(self, path: Path) -> None:
        """记录输出路径。"""
        self.logger.info(f"输出: {path}")

    def log_cache_hit(self, cache_type: str) -> None:
        """记录缓存命中。"""
        self.logger.info(f"缓存命中: {cache_type}")

    def log_cache_miss(self, cache_type: str) -> None:
        """记录缓存未命中。"""
        self.logger.info(f"缓存未命中: {cache_type}，需要重新计算")

    def info(self, message: str) -> None:
        """记录信息。"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """记录警告。"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """记录错误。"""
        self.logger.error(message)