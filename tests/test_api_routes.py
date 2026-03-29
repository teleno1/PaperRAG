from fastapi.testclient import TestClient

from app.api.main import app
from app.domain.models.runtime import ReviewRunResult


def test_state_route(monkeypatch):
    from app.api.routes import pipeline as pipeline_route

    class FakeUseCase:
        def get_state(self):
            from app.domain.models.runtime import ProjectState

            return ProjectState(
                pdf_count=1,
                processed_count=1,
                index_ready=True,
                vector_count=10,
                outlines_count=2,
                latest_run_dir="/tmp/run1",
            )

    monkeypatch.setattr(pipeline_route, "HealthAndStateUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.get("/state")
    assert response.status_code == 200
    assert response.json()["vector_count"] == 10


def test_review_run_from_outline_route(monkeypatch):
    from app.api.routes import review as review_route

    class FakeUseCase:
        def execute(self, outline_path):
            return ReviewRunResult(
                run_id="run-1",
                run_dir=outline_path.parent / "run-1",
                outline_path=outline_path,
                final_review_md=outline_path.parent / "run-1/07_export/final_review.md",
                final_review_txt=outline_path.parent / "run-1/07_export/final_review.txt",
                final_review_json=outline_path.parent / "run-1/07_export/final_review.json",
                references_json=outline_path.parent / "run-1/07_export/references.json",
                validation_report=outline_path.parent / "run-1/06_validation/validation_report.json",
            )

    monkeypatch.setattr(review_route, "RunReviewFromOutlineUseCase", FakeUseCase)
    client = TestClient(app)
    response = client.post("/review/run-from-outline", json={"outline_path": __file__})
    assert response.status_code == 200
    assert response.json()["run_dir"].endswith("run-1")
