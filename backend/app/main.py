"""Application entry point.

Builds the FastAPI app via a small factory so tests can construct an isolated
instance and later phases can wire in routers (accounts, consent, audit log)
without touching a global object.

Run locally:
    uvicorn app.main:app --reload --app-dir backend
or use the convenience script:
    python -m backend.app.main
"""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.api.routes import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        summary="An FDX-aligned Consumer-Driven Banking aggregator with a "
        "first-class consent + traceability layer.",
    )

    # Routers. Later phases register additional routers here:
    #   - accounts / transactions (Phase 3)
    #   - consent grant / revoke + audit log (Phase 2)
    app.include_router(health.router)

    @app.get("/", tags=["meta"], summary="Service root")
    def root() -> dict[str, str]:
        """Friendly root payload pointing at the interactive docs."""
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover - convenience runner
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        app_dir="backend",
    )
