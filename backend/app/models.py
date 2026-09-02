import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "minimum_experience IS NULL OR minimum_experience >= 0",
            name="ck_jobs_minimum_experience_nonnegative",
        ),
        CheckConstraint(
            "maximum_experience IS NULL OR maximum_experience >= 0",
            name="ck_jobs_maximum_experience_nonnegative",
        ),
        CheckConstraint(
            "minimum_experience IS NULL OR maximum_experience IS NULL "
            "OR maximum_experience >= minimum_experience",
            name="ck_jobs_experience_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    minimum_experience: Mapped[int | None] = mapped_column(Integer)
    maximum_experience: Mapped[int | None] = mapped_column(Integer)
    skills: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    parsed_requirements: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )
    calls: Mapped[list["Call"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("job_id", "apollo_id", name="uq_candidates_job_apollo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    apollo_id: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_title: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="candidates")
    calls: Mapped[list["Call"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True
    )


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_calls_duration_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hunar_call_id: Mapped[str | None] = mapped_column(String(255), index=True)
    request_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    summary: Mapped[str | None] = mapped_column(Text)
    recording_url: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    job: Mapped[Job] = relationship(back_populates="calls")
    candidate: Mapped[Candidate] = relationship(back_populates="calls")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_event_id: Mapped[str | None] = mapped_column(String(255), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
