"""Shared exception types for PaperRAG."""

from __future__ import annotations

from typing import Any, Optional


class PaperRAGError(Exception):
    """Base application exception."""

    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - details: {self.details}"
        return self.message


class ConfigurationError(PaperRAGError):
    """Configuration-related failure."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        self.config_key = config_key
        details = f"config key: {config_key}" if config_key else None
        super().__init__(message, details)


class NoPdfFoundError(PaperRAGError):
    """No source PDF files were found."""

    def __init__(self, papers_dir: str):
        super().__init__(
            f"No PDF files found in directory: {papers_dir}",
            {"papers_dir": papers_dir},
        )


class InsufficientPapersError(PaperRAGError):
    """The corpus is too small for review generation."""

    def __init__(self, papers_count: int, min_required: int, papers_dir: str):
        self.papers_count = papers_count
        self.min_required = min_required
        self.papers_dir = papers_dir
        super().__init__(
            "Not enough papers to support review generation.",
            {
                "papers_count": papers_count,
                "min_required": min_required,
                "papers_dir": papers_dir,
            },
        )


class MineruParseError(PaperRAGError):
    """MinerU parsing failed."""

    def __init__(self, pdf_path: str, reason: Optional[str] = None):
        self.pdf_path = pdf_path
        message = f"PDF parsing failed: {pdf_path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, {"pdf_path": pdf_path, "reason": reason})


class IndexBuildError(PaperRAGError):
    """Vector index build failed."""

    def __init__(self, reason: str, processed_dir: Optional[str] = None):
        self.processed_dir = processed_dir
        super().__init__(
            f"Vector index build failed: {reason}",
            {"processed_dir": processed_dir},
        )


class OutlineGenerationError(PaperRAGError):
    """Outline generation failed."""

    def __init__(self, topic: str, reason: Optional[str] = None):
        self.topic = topic
        message = f"Outline generation failed: {topic}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, {"topic": topic, "reason": reason})


class ReviewPipelineError(PaperRAGError):
    """Review pipeline execution failed."""

    def __init__(self, stage: str, reason: str, outline_path: Optional[str] = None):
        self.stage = stage
        self.outline_path = outline_path
        super().__init__(
            f"Review generation stage '{stage}' failed: {reason}",
            {"stage": stage, "outline_path": outline_path},
        )


class RetrievalError(PaperRAGError):
    """Retrieval failed."""

    def __init__(self, query: str, reason: str):
        self.query = query
        super().__init__(
            f"Retrieval failed: {reason}",
            {"query": query},
        )


class DatabaseNotReadyError(PaperRAGError):
    """The vector database is not ready yet."""

    def __init__(self, missing_files: list[str]):
        self.missing_files = missing_files
        super().__init__(
            f"Vector database is not ready. Missing files: {', '.join(missing_files)}",
            {"missing_files": missing_files},
        )


class ApiKeyMissingError(ConfigurationError):
    """An API key is missing."""

    def __init__(self, key_name: str):
        self.key_name = key_name
        super().__init__(
            f"Missing API key: {key_name}. Set it with an environment variable instead of settings.yaml.",
            key_name,
        )
