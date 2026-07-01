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

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import agent, aggregation, consent, health
from app.api.session import (
    COOKIE_MAX_AGE,
    SESSION_COOKIE,
    SessionStore,
    new_session_id,
)
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

    # Per-visitor demo worlds: each browser session gets its own isolated,
    # mutable copy so one visitor's revoke never touches another's. A real
    # deployment builds each world from a database + the connected sources.
    app.state.sessions = SessionStore()

    @app.middleware("http")
    async def ensure_session(request: Request, call_next):
        """Give every visitor a stable session id (cookie) for their own world."""
        session_id = request.cookies.get(SESSION_COOKIE)
        is_new = session_id is None
        if is_new:
            session_id = new_session_id()
        request.state.session_id = session_id

        response = await call_next(request)

        if is_new:
            response.set_cookie(
                SESSION_COOKIE,
                session_id,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
            )
        return response

    app.include_router(health.router)
    app.include_router(consent.router)  # Item 9: consent dashboard API
    app.include_router(aggregation.router)  # Item 10: unified accounts / net worth
    app.include_router(agent.router)  # Item 11: agentic delegation

    dist = _frontend_dist(settings.frontend_dist)
    if dist is None:

        @app.get("/", tags=["meta"], summary="Service root")
        def root() -> dict[str, str]:
            """Friendly root payload pointing at the interactive docs."""
            return {
                "service": settings.app_name,
                "docs": "/docs",
                "health": "/health",
            }
    else:
        # Serve the built single-page app at "/". Mounted last so the explicit
        # /health, /docs and /api/* routes above still win; html=True makes it
        # serve index.html for "/" and unknown client-side routes.
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app


def _frontend_dist(configured: str | None) -> Path | None:
    """Return the built-frontend directory if configured and present, else None."""
    if not configured:
        return None
    path = Path(configured)
    return path if path.is_dir() else None


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
