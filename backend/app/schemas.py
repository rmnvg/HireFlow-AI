import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    location: str | None = Field(default=None, max_length=255)
    minimum_experience: int | None = Field(default=None, ge=0)
    maximum_experience: int | None = Field(default=None, ge=0)
    skills: list[str] = Field(default_factory=list)
    parsed_requirements: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_experience_range(self) -> "JobCreate":
        if (
            self.minimum_experience is not None
            and self.maximum_experience is not None
            and self.maximum_experience < self.minimum_experience
        ):
            raise ValueError(
                "maximum_experience must be greater than or equal to minimum_experience"
            )
        return self


class JobResponse(JobCreate, ORMResponse):
    id: uuid.UUID
    created_at: datetime


class JobAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=20, max_length=100_000)


class JobAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str = Field(max_length=255)
    skills: list[str]
    location: str | None = Field(default=None, max_length=255)
    minimum_experience: int | None = Field(default=None, ge=0)
    maximum_experience: int | None = Field(default=None, ge=0)
    seniority: str | None = Field(default=None, max_length=100)
    search_keywords: str = Field(max_length=1_000)

    @model_validator(mode="after")
    def validate_experience_range(self) -> "JobAnalysis":
        if (
            self.minimum_experience is not None
            and self.maximum_experience is not None
            and self.maximum_experience < self.minimum_experience
        ):
            raise ValueError(
                "maximum_experience must be greater than or equal to minimum_experience"
            )
        return self


class AnalyzedJobCreate(JobAnalysis):
    job_title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=20, max_length=100_000)


class CandidateCreate(BaseModel):
    job_id: uuid.UUID
    apollo_id: str | None = Field(default=None, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    current_title: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    source: str = Field(min_length=1, max_length=100)
    raw_profile: dict[str, Any] = Field(default_factory=dict)


class CandidateResponse(CandidateCreate, ORMResponse):
    id: uuid.UUID
    created_at: datetime


class CandidateSearchResponse(BaseModel):
    job_id: uuid.UUID
    search_keywords: str
    fallback_without_keywords: bool
    review_note: str
    candidates: list[CandidateResponse]


class CandidatePhoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str = Field(min_length=1, max_length=64)


class ManualCandidateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=320)


class CallCreate(BaseModel):
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    hunar_call_id: str | None = Field(default=None, max_length=255)
    request_id: str = Field(min_length=1, max_length=255)
    status: str = Field(min_length=1, max_length=100)
    result: dict[str, Any] | None = None
    summary: str | None = None
    recording_url: HttpUrl | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    raw_response: dict[str, Any] | None = None


class CallResponse(CallCreate, ORMResponse):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CallInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: uuid.UUID
    agent_id: str = Field(min_length=1, max_length=255)
    custom_data: dict[str, Any] = Field(default_factory=dict)


class WebhookEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=255)
    external_event_id: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any]


class WebhookEventResponse(WebhookEventCreate, ORMResponse):
    id: uuid.UUID
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
