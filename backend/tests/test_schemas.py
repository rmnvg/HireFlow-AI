import uuid

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas import CallCreate, CandidateCreate, JobCreate, WebhookEventCreate


def test_job_schema_accepts_valid_experience_range() -> None:
    job = JobCreate(
        title="Backend Engineer",
        description="Build reliable recruiting services.",
        minimum_experience=3,
        maximum_experience=7,
        skills=["Python", "PostgreSQL"],
    )

    assert job.maximum_experience == 7
    assert job.parsed_requirements == {}


def test_job_schema_rejects_inverted_experience_range() -> None:
    with pytest.raises(ValidationError, match="maximum_experience"):
        JobCreate(
            title="Backend Engineer",
            description="Build reliable recruiting services.",
            minimum_experience=8,
            maximum_experience=3,
        )


def test_candidate_call_and_webhook_schemas_validate() -> None:
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    candidate = CandidateCreate(job_id=job_id, name="Aisha Mehta", source="apollo")
    call = CallCreate(
        job_id=job_id,
        candidate_id=candidate_id,
        request_id="request-123",
        status="queued",
        recording_url="https://example.com/recording.mp3",
    )
    event = WebhookEventCreate(event_type="call.completed", payload={"request_id": "request-123"})

    assert candidate.raw_profile == {}
    assert str(call.recording_url) == "https://example.com/recording.mp3"
    assert event.payload["request_id"] == "request-123"


def test_settings_normalize_supabase_url_and_origins() -> None:
    settings = Settings(
        DATABASE_URL="postgresql://user:password@db.example.supabase.co:5432/postgres",
        DATABASE_SSL=True,
        FRONTEND_URL="https://app.example.com/, https://admin.example.com",
    )

    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")
    assert settings.database_ssl is True
    assert settings.allowed_origins == ["https://app.example.com", "https://admin.example.com"]
