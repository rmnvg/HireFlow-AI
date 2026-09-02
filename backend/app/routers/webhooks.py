import json
import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Call, WebhookEvent
from app.services.hunar_webhooks import (
    extract_call_identifiers,
    relevant_webhook_value,
    verify_hunar_signature,
    webhook_event_id,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/hunar", tags=["hunar-webhooks"])
WebhookType = Literal["status", "recording", "result", "summary"]


def find_call(db: Session, payload: dict[str, Any]) -> Call | None:
    request_id, hunar_call_id = extract_call_identifiers(payload)
    filters = []
    if request_id is not None:
        filters.append(Call.request_id == request_id)
    if hunar_call_id is not None:
        filters.append(Call.hunar_call_id == hunar_call_id)
    if not filters:
        return None
    return db.scalar(select(Call).where(or_(*filters)))


def update_call(call: Call | None, event_type: WebhookType, payload: dict[str, Any]) -> None:
    if call is None:
        return
    if event_type == "status":
        call_status = relevant_webhook_value(payload, "status", "call_status")
        if isinstance(call_status, str) and call_status.strip():
            call.status = call_status.strip()
    elif event_type == "recording":
        recording = relevant_webhook_value(payload, "recording_url", "recording")
        if isinstance(recording, dict):
            recording = recording.get("url")
        if isinstance(recording, str) and recording.strip():
            call.recording_url = recording.strip()
    elif event_type == "result":
        result = relevant_webhook_value(payload, "result")
        if result is not None:
            call.result = result if isinstance(result, dict) else {"value": result}
    elif event_type == "summary":
        summary = relevant_webhook_value(payload, "summary")
        if isinstance(summary, str):
            call.summary = summary


async def process_webhook(
    event_type: WebhookType,
    request: Request,
    db: Session,
) -> dict[str, str]:
    raw_body = await request.body()
    settings = get_settings()
    secret = (
        settings.hunar_api_key.get_secret_value()
        if settings.hunar_api_key is not None
        else ""
    )
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hunar webhooks are not configured",
        )
    if not verify_hunar_signature(
        raw_body,
        request.headers.get("X-Hunar-Timestamp"),
        request.headers.get("X-Hunar-Signature"),
        secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Hunar webhook signature",
        )

    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body must be valid JSON",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body must be a JSON object",
        )

    external_event_id = webhook_event_id(event_type, payload, raw_body)
    try:
        existing_event = db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.event_type == event_type,
                WebhookEvent.external_event_id == external_event_id,
            )
        )
        if existing_event is not None:
            return {"status": "ok"}

        event = WebhookEvent(
            event_type=event_type,
            external_event_id=external_event_id,
            payload=payload,
        )
        db.add(event)
        update_call(find_call(db, payload), event_type, payload)
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"status": "ok"}
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Unable to persist Hunar webhook")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process webhook",
        ) from exc
    return {"status": "ok"}


@router.post("/status")
async def hunar_status_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    return await process_webhook("status", request, db)


@router.post("/recording")
async def hunar_recording_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    return await process_webhook("recording", request, db)


@router.post("/result")
async def hunar_result_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    return await process_webhook("result", request, db)


@router.post("/summary")
async def hunar_summary_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    return await process_webhook("summary", request, db)
