import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Job
from app.schemas import (
    CandidatePhoneUpdate,
    CandidateResponse,
    ErrorResponse,
    ManualCandidateCreate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("", response_model=list[CandidateResponse])
def list_candidates(
    job_id: Annotated[uuid.UUID, Query()],
    db: Annotated[Session, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Candidate]:
    try:
        statement = (
            select(Candidate)
            .where(Candidate.job_id == job_id)
            .order_by(Candidate.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.scalars(statement).all())
    except SQLAlchemyError as exc:
        logger.error("Unable to list candidates")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve candidates",
        ) from exc


@router.patch(
    "/{candidate_id}/phone",
    response_model=CandidateResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def update_candidate_phone(
    candidate_id: uuid.UUID,
    request: CandidatePhoneUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Candidate:
    try:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
            )
        candidate.phone = request.phone
        db.commit()
        db.refresh(candidate)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Unable to update candidate phone")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update candidate phone",
        ) from exc
    return candidate


@router.post(
    "/manual",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def create_manual_candidate(
    request: ManualCandidateCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Candidate:
    try:
        if db.get(Job, request.job_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        candidate = Candidate(
            job_id=request.job_id,
            name=request.name,
            phone=request.phone,
            email=request.email,
            source="manual",
            raw_profile={},
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Unable to create manual candidate")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save manual candidate",
        ) from exc
    return candidate
