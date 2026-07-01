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
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.demo import build_demo_state
from app.api.routes import consent, health
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

    # The consent dashboard (Item 9) is a separate React app in ../frontend, so
    # allow it to call this API cross-origin. Open in this local/demo build.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # In-memory demo world the consent dashboard reads and mutates. A real
    # deployment builds this from a database + the connected sources instead.
    app.state.aggregator = build_demo_state()

    # Routers. Phase 3 will add accounts / transactions here.
    app.include_router(health.router)
    app.include_router(consent.router)

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
