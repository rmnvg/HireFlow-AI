import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Job
from app.routers.jobs import get_groq_analyzer
from app.schemas import JobAnalysis
from app.services.groq import GroqInvalidResponseError
from tests.test_groq_service import PYTHON_BACKEND_JD, VALID_ANALYSIS


class SuccessfulAnalyzer:
    def analyze(self, description: str) -> JobAnalysis:
        assert description == PYTHON_BACKEND_JD
        return JobAnalysis.model_validate(VALID_ANALYSIS)


class InvalidAnalyzer:
    def analyze(self, _: str) -> JobAnalysis:
        raise GroqInvalidResponseError("invalid output containing upstream details")


class FakeSession:
    def __init__(self) -> None:
        self.jobs: dict[uuid.UUID, Job] = {}
        self.pending: Job | None = None

    def add(self, job: Job) -> None:
        self.pending = job

    def commit(self) -> None:
        if self.pending is not None:
            self.pending.id = uuid.uuid4()
            self.pending.created_at = datetime.now(UTC)
            self.jobs[self.pending.id] = self.pending

    def refresh(self, _: Job) -> None:
        return None

    def rollback(self) -> None:
        self.pending = None

    def get(self, _: type[Job], job_id: uuid.UUID) -> Job | None:
        return self.jobs.get(job_id)

    def scalars(self, _statement) -> SimpleNamespace:
        return SimpleNamespace(all=lambda: list(self.jobs.values()))


def test_analyze_python_backend_jd_without_calling_groq() -> None:
    app.dependency_overrides[get_groq_analyzer] = lambda: SuccessfulAnalyzer()
    try:
        with TestClient(app) as client:
            response = client.post("/api/jobs/analyze", json={"description": PYTHON_BACKEND_JD})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == VALID_ANALYSIS


def test_analyze_returns_safe_502_after_invalid_outputs() -> None:
    app.dependency_overrides[get_groq_analyzer] = lambda: InvalidAnalyzer()
    try:
        with TestClient(app) as client:
            response = client.post("/api/jobs/analyze", json={"description": PYTHON_BACKEND_JD})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Job analysis service returned invalid data after retry"
    }
    assert "upstream" not in response.text


def test_create_list_and_get_analyzed_job() -> None:
    fake_db = FakeSession()

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db
    payload = {"description": PYTHON_BACKEND_JD, **VALID_ANALYSIS}
    try:
        with TestClient(app) as client:
            created = client.post("/api/jobs", json=payload)
            listed = client.get("/api/jobs")
            fetched = client.get(f"/api/jobs/{created.json()['id']}")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["title"] == "Senior Python Backend Engineer"
    assert created.json()["parsed_requirements"]["seniority"] == "Senior"
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created.json()["id"]
