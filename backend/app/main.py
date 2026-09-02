import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import check_database_connection, init_db
from app.routers.candidates import router as candidates_router
from app.routers.jobs import router as jobs_router
from app.schemas import ErrorResponse

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.database_init_on_startup:
        try:
            init_db()
        except SQLAlchemyError:
            # Keep the API alive so readiness can report a temporary outage.
            logger.error("Database initialization failed; health endpoint will report unavailable")
    yield


app = FastAPI(
    title="HireFlow AI API",
    description="Backend services for the HireFlow AI recruiting platform.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs_router)
app.include_router(candidates_router)


class HealthResponse(BaseModel):
    status: Literal["healthy"]


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Database connectivity is unavailable.",
        }
    },
    tags=["system"],
)
def health() -> HealthResponse:
    try:
        check_database_connection()
    except SQLAlchemyError as exc:
        logger.warning("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return HealthResponse(status="healthy")
