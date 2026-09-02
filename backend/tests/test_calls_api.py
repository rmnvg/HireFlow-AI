import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Call, Candidate, Job
from app.routers.hunar import get_hunar_service
from app.services.hunar import HunarSubscriptionError


class FakeSession:
    def __init__(self, job: Job, candidate: Candidate) -> None:
        self.jobs = {job.id: job}
        self.candidates = {candidate.id: candidate}
        self.calls: dict[uuid.UUID, Call] = {}
        self.pending: list[Call] = []

    def get(self, model, record_id):
        if model is Job:
            return self.jobs.get(record_id)
        if model is Candidate:
            return self.candidates.get(record_id)
        if model is Call:
            return self.calls.get(record_id)
        return None

    def add(self, call: Call) -> None:
        self.pending.append(call)

    def commit(self) -> None:
        now = datetime.now(UTC)
        for call in self.pending:
            call.id = uuid.uuid4()
            call.created_at = now
            call.updated_at = now
            self.calls[call.id] = call
        for call in self.calls.values():
            call.updated_at = now
        self.pending.clear()

    def refresh(self, _record) -> None:
        return None

    def rollback(self) -> None:
        self.pending.clear()

    def scalars(self, _statement) -> SimpleNamespace:
        return SimpleNamespace(all=lambda: list(self.calls.values()))


class FakeHunar:
    def __init__(self) -> None:
        self.created_payloads: list[dict] = []
        self.refreshed_ids: list[str] = []

    def list_agents(self):
        return {"agents": [{"id": "agent-1", "name": "Recruiter"}]}

    def get_agent(self, agent_id: str):
        assert agent_id == "agent-1"
        return {
            "id": agent_id,
            "required_variables": [
                "job_role",
                "job_description",
                "company",
                "location",
                "candidate_language",
            ],
        }

    def create_call(self, payload: dict):
        self.created_payloads.append(payload)
        return {"data": {"call": {"id": "hunar-call-1", "status": "QUEUED"}}}

    def get_call(self, hunar_call_id: str):
        self.refreshed_ids.append(hunar_call_id)
        return {
            "data": {
                "call": {
                    "id": hunar_call_id,
                    "status": "COMPLETED",
                    "duration_seconds": 87,
                    "recording_url": "https://recordings.example.com/call.mp3",
                    "result": {"recommended": True},
                    "summary": "Candidate has relevant Python experience.",
                }
            }
        }


class SubscriptionExhaustedHunar:
    def list_agents(self):
        raise HunarSubscriptionError()


def make_records(phone: str = "+919876543210") -> tuple[Job, Candidate]:
    job = Job(
        title="Python Backend Engineer",
        description="Build FastAPI and PostgreSQL services.",
        location="Bengaluru",
        skills=["Python", "FastAPI"],
        parsed_requirements={},
    )
    job.id = uuid.uuid4()
    job.created_at = datetime.now(UTC)
    candidate = Candidate(
        job_id=job.id,
        name="Aisha Mehta",
        company="Example Labs",
        location="Bengaluru",
        phone=phone,
        source="manual",
        raw_profile={},
    )
    candidate.id = uuid.uuid4()
    candidate.created_at = datetime.now(UTC)
    return job, candidate


def override_database(fake_db: FakeSession):
    def dependency():
        yield fake_db

    return dependency


def test_create_list_get_and_refresh_single_call() -> None:
    job, candidate = make_records()
    fake_db = FakeSession(job, candidate)
    hunar = FakeHunar()
    app.dependency_overrides[get_db] = override_database(fake_db)
    app.dependency_overrides[get_hunar_service] = lambda: hunar
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/calls",
                json={
                    "candidate_id": str(candidate.id),
                    "agent_id": "agent-1",
                    "custom_data": {"candidate_language": "English"},
                },
            )
            listed = client.get("/api/calls")
            fetched = client.get(f"/api/calls/{created.json()['id']}")
            refreshed = client.post(f"/api/calls/{created.json()['id']}/refresh")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["status"] == "QUEUED"
    assert created.json()["hunar_call_id"] == "hunar-call-1"
    payload = hunar.created_payloads[0]
    assert uuid.UUID(payload["request_id"])
    assert payload["mobile_number"] == "+919876543210"
    assert payload["timezone"] == "Asia/Kolkata"
    assert payload["custom_data"] == {
        "candidate_language": "English",
        "job_role": "Python Backend Engineer",
        "job_description": "Build FastAPI and PostgreSQL services.",
        "company": "Example Labs",
        "location": "Bengaluru",
    }
    assert payload["callback_config"] == {
        "status_callback_url": "https://backend.example.com/webhooks/hunar/status",
        "recording_callback_url": "https://backend.example.com/webhooks/hunar/recording",
        "result_callback_url": "https://backend.example.com/webhooks/hunar/result",
        "summary_callback_url": "https://backend.example.com/webhooks/hunar/summary",
    }
    assert len(listed.json()) == 1
    assert fetched.json()["id"] == created.json()["id"]
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "COMPLETED"
    assert refreshed.json()["duration_seconds"] == 87
    assert refreshed.json()["result"] == {"recommended": True}


def test_call_rejects_non_e164_phone_before_contacting_hunar() -> None:
    job, candidate = make_records(phone="9876543210")
    fake_db = FakeSession(job, candidate)
    hunar = FakeHunar()
    app.dependency_overrides[get_db] = override_database(fake_db)
    app.dependency_overrides[get_hunar_service] = lambda: hunar
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/calls",
                json={"candidate_id": str(candidate.id), "agent_id": "agent-1"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {"detail": "Candidate phone must be a valid E.164 number"}
    assert hunar.created_payloads == []


def test_call_requires_every_agent_variable() -> None:
    job, candidate = make_records()
    fake_db = FakeSession(job, candidate)
    hunar = FakeHunar()
    app.dependency_overrides[get_db] = override_database(fake_db)
    app.dependency_overrides[get_hunar_service] = lambda: hunar
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/calls",
                json={"candidate_id": str(candidate.id), "agent_id": "agent-1"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "candidate_language" in response.json()["detail"]
    assert fake_db.calls == {}


def test_hunar_agent_proxy_and_subscription_error() -> None:
    hunar = FakeHunar()
    app.dependency_overrides[get_hunar_service] = lambda: hunar
    try:
        with TestClient(app) as client:
            agents = client.get("/api/hunar/agents")
            agent = client.get("/api/hunar/agents/agent-1")
            app.dependency_overrides[get_hunar_service] = lambda: SubscriptionExhaustedHunar()
            exhausted = client.get("/api/hunar/agents")
    finally:
        app.dependency_overrides.clear()

    assert agents.status_code == 200
    assert agents.json()["agents"][0]["id"] == "agent-1"
    assert agent.status_code == 200
    assert exhausted.status_code == 402
    assert exhausted.json() == {
        "detail": "Hunar subscription or calling minutes are exhausted"
    }
