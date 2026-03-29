"""Configuration loading for PaperRAG.

Priority: environment variables > settings.yaml > code defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.exceptions import ConfigurationError

CONFIG_PATH_ENV = "PAPERRAG_CONFIG_PATH"
FORBIDDEN_YAML_MODEL_KEYS = {
    "deepseek_api_key": "DEEPSEEK_API_KEY",
    "dashscope_api_key": "DASHSCOPE_API_KEY",
    "mineru_api_key": "MINERU_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
}


class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectConfig(StrictConfigModel):
    """Project metadata."""

    name: str = "PaperRAG"


class PathsConfig(StrictConfigModel):
    """Filesystem layout."""

    papers_dir: str = "./data/papers"
    processed_dir: str = "./data/processed_papers"
    database_dir: str = "./data/database"
    outlines_dir: str = "./data/outlines"
    outputs_dir: str = "./data/review_outputs"


class ModelsConfig(StrictConfigModel):
    """Model and endpoint settings."""

    llm_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    embedding_model: str = "text-embedding-v4"
    embedding_dimension: Optional[int] = None
    rerank_model: str = "qwen3-rerank"

    # Secrets are loaded from environment variables only.
    deepseek_api_key: Optional[str] = Field(default=None, exclude=True)
    dashscope_api_key: Optional[str] = Field(default=None, exclude=True)
    mineru_api_key: Optional[str] = Field(default=None, exclude=True)


class PipelineConfig(StrictConfigModel):
    """Pipeline behavior."""

    parallel_body_writing: bool = True
    max_workers: int = 5
    top_k_recall: int = 20
    outline_query_count: int = 5
    min_papers_for_review: int = 15
    temperature_chapter: float = 0.2
    temperature_final_pass: float = 0.2
    max_cites_per_sentence: int = 3
    previous_recap_chars: int = 1200


class MinerUConfig(StrictConfigModel):
    """MinerU PDF parsing settings."""

    upload_url: str = "https://mineru.net/api/v4/file-urls/batch"
    result_url_template: str = "https://mineru.net/api/v4/extract-results/batch/{}"
    poll_interval: int = 5
    max_wait_time: int = 300
    model_version: str = "vlm"


class Settings(StrictConfigModel):
    """Global application settings."""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    mineru: MinerUConfig = Field(default_factory=MinerUConfig)


_settings: Optional[Settings] = None
_config_loaded: bool = False


def _resolve_config_path() -> Path:
    override = os.getenv(CONFIG_PATH_ENV)
    if override:
        return Path(override).expanduser().resolve()
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "configs" / "settings.yaml"


def _load_yaml_config(config_path: Path) -> dict:
    """Load the YAML config file if it exists."""

    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as file_obj:
        payload = yaml.safe_load(file_obj) or {}

    if not isinstance(payload, dict):
        raise ConfigurationError(
            f"Config file must contain a YAML object: {config_path}",
            str(config_path),
        )
    return payload


def _validate_yaml_config(yaml_config: dict) -> None:
    """Reject secrets in YAML so users keep them in environment variables."""

    models_config = yaml_config.get("models", {})
    if not isinstance(models_config, dict):
        return

    for field_name, env_name in FORBIDDEN_YAML_MODEL_KEYS.items():
        if field_name in models_config:
            raise ConfigurationError(
                f"`models.{field_name}` is not allowed in settings.yaml. Set `{env_name}` in the environment instead.",
                f"models.{field_name}",
            )


def _merge_env_to_settings(settings_obj: Settings) -> Settings:
    """Merge environment variables into the settings object."""

    if os.getenv("DEEPSEEK_API_KEY"):
        settings_obj.models.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if os.getenv("DEEPSEEK_BASE_URL"):
        settings_obj.models.deepseek_base_url = os.getenv(
            "DEEPSEEK_BASE_URL",
            settings_obj.models.deepseek_base_url,
        )
    if os.getenv("DEEPSEEK_MODEL"):
        settings_obj.models.llm_model = os.getenv(
            "DEEPSEEK_MODEL",
            settings_obj.models.llm_model,
        )
    if os.getenv("EMBEDDING_DIMENSION"):
        settings_obj.models.embedding_dimension = int(
            os.getenv("EMBEDDING_DIMENSION", str(settings_obj.models.embedding_dimension or "0"))
        )

    if os.getenv("DASHSCOPE_API_KEY"):
        settings_obj.models.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")

    if os.getenv("MINERU_API_KEY"):
        settings_obj.models.mineru_api_key = os.getenv("MINERU_API_KEY")

    if os.getenv("PARALLEL_BODY_WRITING"):
        settings_obj.pipeline.parallel_body_writing = os.getenv("PARALLEL_BODY_WRITING") not in {"0", "false", "False"}
    if os.getenv("BODY_CHAPTER_MAX_WORKERS"):
        settings_obj.pipeline.max_workers = int(
            os.getenv("BODY_CHAPTER_MAX_WORKERS", str(settings_obj.pipeline.max_workers))
        )
    if os.getenv("TEMPERATURE_CHAPTER"):
        settings_obj.pipeline.temperature_chapter = float(
            os.getenv("TEMPERATURE_CHAPTER", str(settings_obj.pipeline.temperature_chapter))
        )
    if os.getenv("TEMPERATURE_FINAL_PASS"):
        settings_obj.pipeline.temperature_final_pass = float(
            os.getenv("TEMPERATURE_FINAL_PASS", str(settings_obj.pipeline.temperature_final_pass))
        )
    if os.getenv("MIN_PAPERS_FOR_REVIEW"):
        settings_obj.pipeline.min_papers_for_review = int(
            os.getenv("MIN_PAPERS_FOR_REVIEW", str(settings_obj.pipeline.min_papers_for_review))
        )

    return settings_obj


def get_settings() -> Settings:
    """Get the singleton settings instance."""

    global _settings, _config_loaded, settings

    if _settings is not None:
        return _settings

    config_path = _resolve_config_path()
    yaml_config = _load_yaml_config(config_path)
    _validate_yaml_config(yaml_config)

    try:
        _settings = Settings(**yaml_config)
    except ValidationError as exc:
        raise ConfigurationError(
            f"Invalid configuration file: {config_path}",
            exc.errors(),
        ) from exc

    _settings = _merge_env_to_settings(_settings)
    _config_loaded = True
    settings = _settings
    return _settings


def reload_settings() -> Settings:
    """Reload the settings and invalidate cached paths."""

    global _settings, _config_loaded, settings
    _settings = None
    _config_loaded = False
    refreshed = get_settings()

    try:
        from app.core.paths import reload_paths

        reload_paths()
    except Exception:
        pass

    settings = refreshed
    return refreshed


settings: Settings = get_settings()
