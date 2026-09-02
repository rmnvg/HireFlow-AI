import logging
import uuid
from collections.abc import Generator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from groq import Groq
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Candidate, Job
from app.schemas import (
    AnalyzedJobCreate,
    CandidateSearchResponse,
    ErrorResponse,
    JobAnalysis,
    JobAnalysisRequest,
    JobResponse,
)
from app.services.apollo import (
    ApolloAuthenticationError,
    ApolloContactService,
    ApolloPermissionError,
    ApolloRateLimitError,
    ApolloTimeoutError,
    ApolloUnavailableError,
    normalize_apollo_contact,
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


def get_apollo_service() -> Generator[ApolloContactService, None, None]:
    settings = get_settings()
    if settings.apollo_api_key is None or not settings.apollo_api_key.get_secret_value().strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Apollo candidate search is not configured",
        )

    timeout = httpx.Timeout(
        settings.apollo_timeout_seconds,
        connect=min(10.0, settings.apollo_timeout_seconds),
    )
    with httpx.Client() as client:
        yield ApolloContactService(
            client=client,
            api_key=settings.apollo_api_key.get_secret_value(),
            contacts_url=settings.apollo_contacts_url,
            timeout=timeout,
        )


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


@router.post(
    "/{job_id}/search-candidates",
    response_model=CandidateSearchResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
        status.HTTP_504_GATEWAY_TIMEOUT: {"model": ErrorResponse},
    },
)
def search_candidates(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    apollo: Annotated[ApolloContactService, Depends(get_apollo_service)],
) -> CandidateSearchResponse:
    try:
        job = db.get(Job, job_id)
    except SQLAlchemyError as exc:
        logger.error("Unable to load job for candidate search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load job",
        ) from exc
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    parsed_requirements = job.parsed_requirements or {}
    raw_keywords = parsed_requirements.get("search_keywords")
    search_keywords = raw_keywords.strip() if isinstance(raw_keywords, str) else ""

    try:
        result = apollo.search_contacts(search_keywords)
    except ApolloAuthenticationError as exc:
        logger.warning("Apollo rejected candidate search credentials")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Apollo rejected the configured API credentials",
        ) from exc
    except ApolloPermissionError as exc:
        logger.warning("Apollo denied contact search access")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Apollo API credentials do not have contact search access",
        ) from exc
    except ApolloRateLimitError as exc:
        logger.warning("Apollo candidate search rate limit reached")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Apollo rate limit reached; retry later",
        ) from exc
    except ApolloTimeoutError as exc:
        logger.warning("Apollo candidate search timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Apollo candidate search timed out",
        ) from exc
    except ApolloUnavailableError as exc:
        logger.warning("Apollo candidate search failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Apollo candidate search is unavailable",
        ) from exc

    normalized_by_id: dict[str, dict] = {}
    for contact in result.contacts:
        normalized = normalize_apollo_contact(contact, job.id)
        if normalized is not None:
            normalized_by_id.setdefault(normalized["apollo_id"], normalized)

    apollo_ids = list(normalized_by_id)
    try:
        existing_candidates = []
        if apollo_ids:
            statement = select(Candidate).where(
                Candidate.job_id == job.id,
                Candidate.apollo_id.in_(apollo_ids),
            )
            existing_candidates = list(db.scalars(statement).all())

        candidates_by_apollo = {
            candidate.apollo_id: candidate
            for candidate in existing_candidates
            if candidate.apollo_id is not None
        }
        new_candidates = [
            Candidate(**normalized)
            for apollo_id, normalized in normalized_by_id.items()
            if apollo_id not in candidates_by_apollo
        ]
        if new_candidates:
            db.add_all(new_candidates)
            db.commit()
            for candidate in new_candidates:
                db.refresh(candidate)
                if candidate.apollo_id is not None:
                    candidates_by_apollo[candidate.apollo_id] = candidate
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Unable to save Apollo candidates")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save candidates",
        ) from exc

    saved_candidates = [
        candidates_by_apollo[apollo_id]
        for apollo_id in normalized_by_id
        if apollo_id in candidates_by_apollo
    ]
    if result.fallback_without_keywords:
        review_note = (
            "Keyword search returned no saved Apollo contacts. These unfiltered workspace "
            "contacts are provided for recruiter review and are not guaranteed matches."
        )
    else:
        review_note = (
            "Contacts came from the saved Apollo workspace using the job keywords; "
            "recruiter review is still required."
        )

    return CandidateSearchResponse(
        job_id=job.id,
        search_keywords=search_keywords,
        fallback_without_keywords=result.fallback_without_keywords,
        review_note=review_note,
        candidates=saved_candidates,
    )


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
