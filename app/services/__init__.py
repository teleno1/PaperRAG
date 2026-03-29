"""服务层模块。"""

from __future__ import annotations

__all__ = [
    "ParserService",
    "IndexService",
    "OutlineService",
    "ReviewService",
    "PipelineService",
]


# 延迟导入，避免循环依赖
def __getattr__(name: str):
    if name == "ParserService":
        from app.services.parser_service import ParserService
        return ParserService
    elif name == "IndexService":
        from app.services.index_service import IndexService
        return IndexService
    elif name == "OutlineService":
        from app.services.outline_service import OutlineService
        return OutlineService
    elif name == "ReviewService":
        from app.services.review_service import ReviewService
        return ReviewService
    elif name == "PipelineService":
        from app.services.pipeline_service import PipelineService
        return PipelineService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")