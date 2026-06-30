"""Health-check endpoint.

A trivial liveness probe used to confirm the service is up and to give CI / a
load balancer something to hit. Intentionally does no auth and touches no data —
it must stay cheap and dependency-free.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Shape of the health-check payload."""

    status: str
    service: str
    environment: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health() -> HealthResponse:
    """Return basic service metadata to confirm the app is running."""

    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        version=__version__,
    )
