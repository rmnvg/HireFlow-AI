import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Candidate, Job
from app.routers.jobs import get_apollo_service
from app.services.apollo import (
    ApolloAuthenticationError,
    ApolloPermissionError,
    ApolloRateLimitError,
    ApolloSearchResult,
    ApolloTimeoutError,
)


class FakeSession:
    def __init__(self, job: Job) -> None:
        self.jobs = {job.id: job}
        self.candidates: dict[uuid.UUID, Candidate] = {}
        self.pending: list[Candidate] = []

    def get(self, model, record_id):
        if model is Job:
            return self.jobs.get(record_id)
        if model is Candidate:
            return self.candidates.get(record_id)
        return None

    def add(self, candidate: Candidate) -> None:
        self.pending.append(candidate)

    def add_all(self, candidates: list[Candidate]) -> None:
        self.pending.extend(candidates)

    def commit(self) -> None:
        for candidate in self.pending:
            candidate.id = uuid.uuid4()
            candidate.created_at = datetime.now(UTC)
            self.candidates[candidate.id] = candidate
        self.pending.clear()

    def refresh(self, _record) -> None:
        return None

    def rollback(self) -> None:
        self.pending.clear()

    def scalars(self, _statement) -> SimpleNamespace:
        return SimpleNamespace(all=lambda: list(self.candidates.values()))


class FakeApollo:
    def __init__(self, result: ApolloSearchResult) -> None:
        self.result = result
        self.searches: list[str] = []

    def search_contacts(self, search_keywords: str) -> ApolloSearchResult:
        self.searches.append(search_keywords)
        return self.result


class FailingApollo:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def search_contacts(self, _search_keywords: str) -> ApolloSearchResult:
        raise self.error


def make_job() -> Job:
    job = Job(
        title="Python Backend Engineer",
        description="Build Python backend services using FastAPI and PostgreSQL.",
        skills=["Python", "FastAPI", "PostgreSQL"],
        parsed_requirements={"search_keywords": "Python FastAPI PostgreSQL"},
    )
    job.id = uuid.uuid4()
    job.created_at = datetime.now(UTC)
    return job


def override_database(fake_db: FakeSession):
    def dependency():
        yield fake_db

    return dependency


def test_search_candidates_normalizes_saves_and_deduplicates() -> None:
    job = make_job()
    fake_db = FakeSession(job)
    raw_contact = {
        "id": "apollo-1",
        "name": "Aisha Mehta",
        "title": "Backend Engineer",
        "organization_name": "Example Labs",
        "city": "Bengaluru",
        "email": "aisha@example.com",
    }
    apollo = FakeApollo(ApolloSearchResult([raw_contact, raw_contact], False))
    app.dependency_overrides[get_db] = override_database(fake_db)
    app.dependency_overrides[get_apollo_service] = lambda: apollo
    try:
        with TestClient(app) as client:
            first = client.post(f"/api/jobs/{job.id}/search-candidates")
            second = client.post(f"/api/jobs/{job.id}/search-candidates")
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["fallback_without_keywords"] is False
    assert len(first.json()["candidates"]) == 1
    assert first.json()["candidates"][0]["raw_profile"] == raw_contact
    assert len(second.json()["candidates"]) == 1
    assert len(fake_db.candidates) == 1
    assert apollo.searches == ["Python FastAPI PostgreSQL", "Python FastAPI PostgreSQL"]


def test_fallback_response_requires_recruiter_review() -> None:
    job = make_job()
    fake_db = FakeSession(job)
    apollo = FakeApollo(ApolloSearchResult([], True))
    app.dependency_overrides[get_db] = override_database(fake_db)
    app.dependency_overrides[get_apollo_service] = lambda: apollo
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/jobs/{job.id}/search-candidates")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["fallback_without_keywords"] is True
    assert "not guaranteed matches" in response.json()["review_note"]


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (ApolloAuthenticationError(), 502, "Apollo rejected the configured API credentials"),
        (
            ApolloPermissionError(),
            502,
            "Apollo API credentials do not have contact search access",
        ),
        (ApolloRateLimitError(), 429, "Apollo rate limit reached; retry later"),
        (ApolloTimeoutError(), 504, "Apollo candidate search timed out"),
    ],
)
def test_candidate_search_maps_apollo_errors(error, status_code, detail) -> None:
    job = make_job()
    fake_db = FakeSession(job)
    app.dependency_overrides[get_db] = override_database(fake_db)
    app.dependency_overrides[get_apollo_service] = lambda: FailingApollo(error)
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/jobs/{job.id}/search-candidates")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


def test_manual_candidate_list_and_phone_update() -> None:
    job = make_job()
    fake_db = FakeSession(job)
    app.dependency_overrides[get_db] = override_database(fake_db)
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/candidates/manual",
                json={
                    "job_id": str(job.id),
                    "name": "Rohan Kapoor",
                    "phone": "+919876543210",
                    "email": "rohan@example.com",
                },
            )
            listed = client.get("/api/candidates", params={"job_id": str(job.id)})
            updated = client.patch(
                f"/api/candidates/{created.json()['id']}/phone",
                json={"phone": "+919999999999"},
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["source"] == "manual"
    assert len(listed.json()) == 1
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+919999999999"
