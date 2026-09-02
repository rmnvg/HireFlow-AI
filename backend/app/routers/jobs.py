import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from groq import Groq
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Job
from app.schemas import (
    AnalyzedJobCreate,
    ErrorResponse,
    JobAnalysis,
    JobAnalysisRequest,
    JobResponse,
)
from app.services.groq import (
    GroqInvalidResponseError,
    GroqJobAnalyzer,
    GroqUnavailableError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def get_groq_analyzer() -> GroqJobAnalyzer:
    settings = get_settings()
    if settings.groq_api_key is None or not settings.groq_api_key.get_secret_value().strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq job analysis is not configured",
        )

    client = Groq(
        api_key=settings.groq_api_key.get_secret_value(),
        timeout=settings.groq_timeout_seconds,
    )
    return GroqJobAnalyzer(client=client, model=settings.groq_model)


@router.post(
    "/analyze",
    response_model=JobAnalysis,
    responses={status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse}},
)
def analyze_job(
    request: JobAnalysisRequest,
    analyzer: Annotated[GroqJobAnalyzer, Depends(get_groq_analyzer)],
) -> JobAnalysis:
    try:
        return analyzer.analyze(request.description)
    except GroqInvalidResponseError as exc:
        logger.warning("Groq returned invalid job analysis data after retry")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Job analysis service returned invalid data after retry",
        ) from exc
    except GroqUnavailableError as exc:
        logger.warning("Groq job analysis request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Job analysis service is unavailable",
        ) from exc


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}},
)
def create_job(
    request: AnalyzedJobCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    job = Job(
        title=request.job_title,
        description=request.description,
        location=request.location,
        minimum_experience=request.minimum_experience,
        maximum_experience=request.maximum_experience,
        skills=request.skills,
        parsed_requirements={
            "seniority": request.seniority,
            "search_keywords": request.search_keywords,
        },
    )
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Unable to save analyzed job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save job",
        ) from exc
    return job


@router.get("", response_model=list[JobResponse])
def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Job]:
    try:
        statement = select(Job).order_by(Job.created_at.desc()).offset(offset).limit(limit)
        return list(db.scalars(statement).all())
    except SQLAlchemyError as exc:
        logger.error("Unable to list jobs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve jobs",
        ) from exc


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def get_job(job_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> Job:
    try:
        job = db.get(Job, job_id)
    except SQLAlchemyError as exc:
        logger.error("Unable to retrieve job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve job",
        ) from exc

    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
