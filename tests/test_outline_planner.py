from textwrap import dedent

from app.core import config
from app.domain.outline.planner import OutlinePlanner


def _write_settings(path, body: str) -> None:
    path.write_text(dedent(body).strip() + "\n", encoding="utf-8")


class FakeRetrievalService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, top_k: int = 20):
        self.calls.append((query, top_k))
        return []


class FakeJsonClient:
    pass


def test_outline_planner_uses_configured_top_k_recall(monkeypatch, tmp_path):
    config_path = tmp_path / "settings.yaml"
    _write_settings(
        config_path,
        """
        pipeline:
          top_k_recall: 7
        """,
    )
    monkeypatch.setenv("PAPERRAG_CONFIG_PATH", str(config_path))
    config._settings = None

    retrieval = FakeRetrievalService()
    planner = OutlinePlanner(retrieval_service=retrieval, llm_client=FakeJsonClient())
    planner.retrieve_chunks(["q1", "q2"])

    assert retrieval.calls == [("q1", 7), ("q2", 7)]
