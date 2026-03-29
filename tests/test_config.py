from textwrap import dedent

import pytest

from app.core import config
from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.core.paths import PathManager, get_paths


def _write_settings(path, body: str) -> None:
    path.write_text(dedent(body).strip() + "\n", encoding="utf-8")


def test_config_import():
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_config_default_values():
    config._settings = None
    settings = get_settings()
    assert settings.project.name == "PaperRAG"
    assert settings.paths.papers_dir == "./data/papers"
    assert settings.paths.outputs_dir == "./data/review_outputs"
    assert settings.pipeline.min_papers_for_review == 15


def test_config_yaml_values_take_effect(tmp_path, monkeypatch):
    config_path = tmp_path / "settings.yaml"
    _write_settings(
        config_path,
        """
        project:
          name: DemoRAG
        paths:
          papers_dir: ./custom/papers
          processed_dir: ./custom/processed
          database_dir: ./custom/database
          outlines_dir: ./custom/outlines
          outputs_dir: ./custom/outputs
        models:
          llm_model: demo-chat
          deepseek_base_url: https://example.com/v1
          embedding_model: demo-embedding
          embedding_dimension: 768
          rerank_model: demo-rerank
        pipeline:
          parallel_body_writing: false
          max_workers: 2
          top_k_recall: 9
          outline_query_count: 3
          min_papers_for_review: 4
          temperature_chapter: 0.5
          temperature_final_pass: 0.6
          max_cites_per_sentence: 2
          previous_recap_chars: 800
        mineru:
          upload_url: https://mineru.example/upload
          result_url_template: https://mineru.example/result/{}
          poll_interval: 9
          max_wait_time: 99
          model_version: demo
        """,
    )
    monkeypatch.setenv("PAPERRAG_CONFIG_PATH", str(config_path))
    config._settings = None

    settings = config.get_settings()

    assert settings.project.name == "DemoRAG"
    assert settings.paths.outputs_dir == "./custom/outputs"
    assert settings.models.llm_model == "demo-chat"
    assert settings.models.deepseek_base_url == "https://example.com/v1"
    assert settings.models.embedding_model == "demo-embedding"
    assert settings.models.embedding_dimension == 768
    assert settings.pipeline.parallel_body_writing is False
    assert settings.pipeline.top_k_recall == 9
    assert settings.pipeline.previous_recap_chars == 800
    assert settings.mineru.poll_interval == 9


def test_config_env_override(monkeypatch, tmp_path):
    config_path = tmp_path / "settings.yaml"
    _write_settings(
        config_path,
        """
        models:
          llm_model: yaml-model
          embedding_dimension: 1024
        pipeline:
          max_workers: 2
        """,
    )
    monkeypatch.setenv("PAPERRAG_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test_key_123")
    monkeypatch.setenv("DEEPSEEK_MODEL", "env-model")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "512")
    monkeypatch.setenv("BODY_CHAPTER_MAX_WORKERS", "7")
    config._settings = None

    settings = config.get_settings()

    assert settings.models.deepseek_api_key == "test_key_123"
    assert settings.models.llm_model == "env-model"
    assert settings.models.embedding_dimension == 512
    assert settings.pipeline.max_workers == 7


def test_config_rejects_api_keys_in_yaml(monkeypatch, tmp_path):
    config_path = tmp_path / "settings.yaml"
    _write_settings(
        config_path,
        """
        models:
          deepseek_api_key: should-not-be-here
        """,
    )
    monkeypatch.setenv("PAPERRAG_CONFIG_PATH", str(config_path))
    config._settings = None

    with pytest.raises(ConfigurationError, match="environment"):
        config.get_settings()


def test_paths_manager():
    paths = get_paths()
    assert isinstance(paths, PathManager)
    assert paths.papers_dir.name == "papers"
    assert paths.outputs_dir.name == "review_outputs"
