"""路径管理模块。

提供统一的路径访问接口，所有路径来自配置。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import get_settings


class PathManager:
    """路径管理器。"""

    def __init__(self, settings_override: Optional[object] = None):
        """初始化路径管理器。

        Args:
            settings_override: 可选的配置覆盖，主要用于测试
        """
        self._settings = settings_override or get_settings()
        self._project_root = Path(__file__).resolve().parent.parent.parent

    def _resolve_path(self, path_str: str) -> Path:
        """解析路径，支持相对路径和绝对路径。"""
        path = Path(path_str)
        if path.is_absolute():
            return path
        return self._project_root / path

    @property
    def project_root(self) -> Path:
        """项目根目录。"""
        return self._project_root

    @property
    def papers_dir(self) -> Path:
        """原始论文PDF目录。"""
        return self._resolve_path(self._settings.paths.papers_dir)

    @property
    def processed_dir(self) -> Path:
        """解析后的论文目录。"""
        return self._resolve_path(self._settings.paths.processed_dir)

    @property
    def database_dir(self) -> Path:
        """向量数据库目录。"""
        return self._resolve_path(self._settings.paths.database_dir)

    @property
    def outlines_dir(self) -> Path:
        """大纲输出目录。"""
        return self._resolve_path(self._settings.paths.outlines_dir)

    @property
    def outputs_dir(self) -> Path:
        """综述输出目录。"""
        return self._resolve_path(self._settings.paths.outputs_dir)

    @property
    def faiss_index_path(self) -> Path:
        """FAISS索引文件路径。"""
        return self.database_dir / "paper_index.faiss"

    @property
    def metadata_path(self) -> Path:
        """元数据文件路径。"""
        return self.database_dir / "metadata.json"

    def ensure_dirs(self) -> None:
        """确保所有必要目录存在。"""
        for path in [
            self.papers_dir,
            self.processed_dir,
            self.database_dir,
            self.outlines_dir,
            self.outputs_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def get_outline_path(self, slug: str) -> Path:
        """获取大纲文件路径。

        Args:
            slug: 大纲标识符（如时间戳或主题slug）

        Returns:
            大纲JSON文件路径
        """
        return self.outlines_dir / slug / "outline.json"

    def get_run_output_dir(self, run_id: str) -> Path:
        """获取运行输出目录。

        Args:
            run_id: 运行标识符

        Returns:
            运行输出目录路径
        """
        return self.outputs_dir / run_id


# 全局实例
_paths: Optional[PathManager] = None


def get_paths() -> PathManager:
    """获取全局路径管理器实例。"""
    global _paths
    if _paths is None:
        _paths = PathManager()
    return _paths


def reload_paths() -> PathManager:
    """重新加载路径管理器。"""
    global _paths
    _paths = None
    return get_paths()
