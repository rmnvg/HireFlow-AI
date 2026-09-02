from collections.abc import Generator
from typing import Annotated, Any, NoReturn

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.schemas import ErrorResponse
from app.services.hunar import (
    HunarAuthenticationError,
    HunarFieldError,
    HunarNotFoundError,
    HunarProviderError,
    HunarRateLimitError,
    HunarServiceError,
    HunarSubscriptionError,
    HunarTimeoutError,
    HunarValidationError,
    HunarVoiceService,
)

router = APIRouter(prefix="/api/hunar", tags=["hunar"])


def get_hunar_service() -> Generator[HunarVoiceService, None, None]:
    settings = get_settings()
    if settings.hunar_api_key is None or not settings.hunar_api_key.get_secret_value().strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Hunar Voice is not configured",
        )

    timeout = httpx.Timeout(
        settings.hunar_timeout_seconds,
        connect=min(10.0, settings.hunar_timeout_seconds),
    )
    with httpx.Client() as client:
        yield HunarVoiceService(
            client=client,
            api_key=settings.hunar_api_key.get_secret_value(),
            base_url=settings.hunar_base_url,
            timeout=timeout,
        )


def raise_hunar_http_error(error: HunarServiceError) -> NoReturn:
    if isinstance(error, HunarValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
        detail = "Hunar rejected the request as invalid"
    elif isinstance(error, HunarAuthenticationError):
        status_code = status.HTTP_502_BAD_GATEWAY
        detail = "The configured Hunar API key is invalid"
    elif isinstance(error, HunarSubscriptionError):
        status_code = status.HTTP_402_PAYMENT_REQUIRED
        detail = "Hunar subscription or calling minutes are exhausted"
    elif isinstance(error, HunarNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
        detail = "Hunar resource not found"
    elif isinstance(error, HunarFieldError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        detail = "Hunar rejected one or more request fields"
    elif isinstance(error, HunarRateLimitError):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
        detail = "Hunar rate limit reached; retry later"
    elif isinstance(error, HunarTimeoutError):
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
        detail = "Hunar request timed out"
    elif isinstance(error, HunarProviderError):
        status_code = status.HTTP_502_BAD_GATEWAY
        detail = "Hunar Voice provider is unavailable"
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
        detail = "Hunar Voice request failed"
    raise HTTPException(status_code=status_code, detail=detail) from error


HUNAR_ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_402_PAYMENT_REQUIRED: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
    status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
    status.HTTP_504_GATEWAY_TIMEOUT: {"model": ErrorResponse},
}


@router.get("/agents", responses=HUNAR_ERROR_RESPONSES)
def list_hunar_agents(
    hunar: Annotated[HunarVoiceService, Depends(get_hunar_service)],
) -> Any:
    try:
        return hunar.list_agents()
    except HunarServiceError as exc:
        raise_hunar_http_error(exc)


@router.get("/agents/{agent_id}", responses=HUNAR_ERROR_RESPONSES)
def get_hunar_agent(
    agent_id: str,
    hunar: Annotated[HunarVoiceService, Depends(get_hunar_service)],
) -> dict[str, Any]:
    try:
        return hunar.get_agent(agent_id)
    except HunarServiceError as exc:
        raise_hunar_http_error(exc)
