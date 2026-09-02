import logging
import re
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Call, Candidate, Job
from app.routers.hunar import (
    HUNAR_ERROR_RESPONSES,
    get_hunar_service,
    raise_hunar_http_error,
)
from app.schemas import CallInitiateRequest, CallResponse, ErrorResponse
from app.services.hunar import (
    HunarServiceError,
    HunarVoiceService,
    extract_required_agent_variables,
    get_hunar_call_id,
    unwrap_hunar_data,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calls", tags=["calls"])
E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")
STANDARD_JOB_VARIABLES = {"job_role", "job_description", "company", "location"}


def build_callback_config(public_backend_url: str) -> dict[str, str]:
    base_url = public_backend_url.rstrip("/")
    return {
        "status_callback_url": f"{base_url}/webhooks/hunar/status",
        "recording_callback_url": f"{base_url}/webhooks/hunar/recording",
        "result_callback_url": f"{base_url}/webhooks/hunar/result",
        "summary_callback_url": f"{base_url}/webhooks/hunar/summary",
    }


def build_required_custom_data(
    required_variables: list[str],
    supplied_data: dict[str, Any],
    candidate: Candidate,
    job: Job,
) -> dict[str, Any]:
    standard_values = {
        "job_role": job.title,
        "job_description": job.description,
        "company": candidate.company,
        "location": job.location or candidate.location,
    }
    custom_data = {
        key: value for key, value in supplied_data.items() if key not in STANDARD_JOB_VARIABLES
    }
    missing_variables: list[str] = []
    for variable in required_variables:
        value = standard_values.get(variable)
        if value is None or value == "":
            value = supplied_data.get(variable)
        if value is None or value == "":
            missing_variables.append(variable)
        else:
            custom_data[variable] = value

    if missing_variables:
        missing = ", ".join(sorted(missing_variables))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Missing custom_data required by the selected Hunar agent: {missing}",
        )
    return custom_data


def mark_call_failed(db: Session, call: Call) -> None:
    try:
        call.status = "FAILED"
        db.commit()
        db.refresh(call)
    except SQLAlchemyError:
        db.rollback()
        logger.error("Unable to mark local call as failed")


@router.post(
    "",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
    responses={**HUNAR_ERROR_RESPONSES, status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def create_call(
    request: CallInitiateRequest,
    db: Annotated[Session, Depends(get_db)],
    hunar: Annotated[HunarVoiceService, Depends(get_hunar_service)],
) -> Call:
    try:
        candidate = db.get(Candidate, request.candidate_id)
        if candidate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
            )
        job = db.get(Job, candidate.job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error("Unable to load candidate and job for call")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load candidate and job",
        ) from exc

    phone = candidate.phone.strip() if isinstance(candidate.phone, str) else ""
    if not E164_PATTERN.fullmatch(phone):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Candidate phone must be a valid E.164 number",
        )

    try:
        agent = hunar.get_agent(request.agent_id)
    except HunarServiceError as exc:
        raise_hunar_http_error(exc)
    required_variables = extract_required_agent_variables(agent)
    custom_data = build_required_custom_data(
        required_variables, request.custom_data, candidate, job
    )

    request_id = str(uuid.uuid4())
    local_call = Call(
        job_id=job.id,
        candidate_id=candidate.id,
        request_id=request_id,
        status="REQUESTED",
    )
    try:
        db.add(local_call)
        db.commit()
        db.refresh(local_call)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Unable to create local call record")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create call record",
        ) from exc

    settings = get_settings()
    payload = {
        "agent_id": request.agent_id,
        "callee_name": candidate.name,
        "mobile_number": phone,
        "custom_data": custom_data,
        "request_id": request_id,
        "timezone": "Asia/Kolkata",
        "callback_config": build_callback_config(settings.public_backend_url),
    }
    try:
        provider_response = hunar.create_call(payload)
        hunar_call_id = get_hunar_call_id(provider_response)
        if hunar_call_id is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Hunar returned a call without an identifier",
            )
        provider_data = unwrap_hunar_data(provider_response)
        provider_status = provider_data.get("status") or provider_data.get("call_status")
        local_call.hunar_call_id = hunar_call_id
        if isinstance(provider_status, str) and provider_status.strip():
            local_call.status = provider_status.strip()
        local_call.raw_response = provider_response
        db.commit()
        db.refresh(local_call)
    except HTTPException:
        mark_call_failed(db, local_call)
        raise
    except HunarServiceError as exc:
        mark_call_failed(db, local_call)
        raise_hunar_http_error(exc)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Unable to save Hunar call response")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update call record",
        ) from exc
    return local_call


@router.get("", response_model=list[CallResponse])
def list_calls(
    db: Annotated[Session, Depends(get_db)],
    job_id: Annotated[uuid.UUID | None, Query()] = None,
    candidate_id: Annotated[uuid.UUID | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Call]:
    statement = select(Call)
    if job_id is not None:
        statement = statement.where(Call.job_id == job_id)
    if candidate_id is not None:
        statement = statement.where(Call.candidate_id == candidate_id)
    statement = statement.order_by(Call.created_at.desc()).offset(offset).limit(limit)
    try:
        return list(db.scalars(statement).all())
    except SQLAlchemyError as exc:
        logger.error("Unable to list calls")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve calls",
        ) from exc


@router.get(
    "/{call_id}",
    response_model=CallResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def get_call(call_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> Call:
    try:
        call = db.get(Call, call_id)
    except SQLAlchemyError as exc:
        logger.error("Unable to retrieve call")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve call",
        ) from exc
    if call is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    return call


@router.post(
    "/{call_id}/refresh",
    response_model=CallResponse,
    responses={**HUNAR_ERROR_RESPONSES, status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def refresh_call(
    call_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    hunar: Annotated[HunarVoiceService, Depends(get_hunar_service)],
) -> Call:
    try:
        call = db.get(Call, call_id)
    except SQLAlchemyError as exc:
        logger.error("Unable to retrieve call for refresh")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve call",
        ) from exc
    if call is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    if not call.hunar_call_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Call has no Hunar identifier and cannot be refreshed",
        )

    try:
        provider_response = hunar.get_call(call.hunar_call_id)
    except HunarServiceError as exc:
        raise_hunar_http_error(exc)

    data = unwrap_hunar_data(provider_response)
    provider_status = data.get("status") or data.get("call_status")
    if isinstance(provider_status, str) and provider_status.strip():
        call.status = provider_status.strip()

    duration = data.get("duration_seconds", data.get("duration"))
    try:
        call.duration_seconds = max(0, int(duration)) if duration is not None else None
    except (TypeError, ValueError):
        call.duration_seconds = None

    recording = data.get("recording_url") or data.get("recording")
    if isinstance(recording, dict):
        recording = recording.get("url")
    call.recording_url = recording if isinstance(recording, str) and recording else None

    result = data.get("result")
    call.result = (
        result
        if isinstance(result, dict)
        else ({"value": result} if result is not None else None)
    )
    summary = data.get("summary")
    call.summary = summary if isinstance(summary, str) else None
    call.raw_response = provider_response

    try:
        db.commit()
        db.refresh(call)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Unable to save refreshed Hunar call")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update call record",
        ) from exc
    return call
