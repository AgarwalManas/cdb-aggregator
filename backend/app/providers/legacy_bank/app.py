"""The legacy bank's FastAPI application.

Endpoints (note the un-FDX-like, ad-hoc shape):

* ``POST /api/login`` — username/password -> opaque session id.
* ``GET  /api/profile`` — the messy customer profile.
* ``GET  /api/accounts`` — ONE nested blob: accounts with embedded balances,
  transactions, and positions.

Protected endpoints require an ``X-Session-Id`` header. There are no scopes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import data
from .auth import (
    LEGACY_PASS,
    LEGACY_USER,
    SESSION_TTL_SECONDS,
    Session,
    SessionStore,
    get_session,
)


class LoginRequest(BaseModel):
    """Login body. Note the legacy-style ``pass`` key (aliased; it's a keyword)."""

    model_config = ConfigDict(populate_by_name=True)

    user: str
    password: str = Field(alias="pass")


def create_app() -> FastAPI:
    """Construct the legacy bank app with its own isolated session store."""

    app = FastAPI(
        title="Legacy Bank (messy schema)",
        version="0.0.0",
        summary="A deliberately un-FDX mock source: session auth, nested ad-hoc JSON.",
    )
    app.state.session_store = SessionStore()

    @app.get("/", tags=["meta"], summary="Service root")
    def root() -> dict[str, object]:
        return {
            "service": "Legacy Bank",
            "loginEndpoint": "/api/login",
            "note": "messy, non-FDX schema — exists to exercise the normalizer",
            "docs": "/docs",
        }

    @app.post("/api/login", tags=["auth"], summary="Exchange credentials for a session id")
    def login(body: LoginRequest) -> dict[str, object]:
        if body.user != LEGACY_USER or body.password != LEGACY_PASS:
            # Legacy-style flat error; not OAuth2.
            raise HTTPException(status_code=401, detail="bad credentials")
        session = app.state.session_store.open()
        return {"sid": session.sid, "ttlSeconds": SESSION_TTL_SECONDS}

    @app.get(
        "/api/profile",
        tags=["data"],
        summary="Customer profile (messy shape)",
        dependencies=[Depends(get_session)],
    )
    def profile() -> dict[str, object]:
        return data.PROFILE

    @app.get(
        "/api/accounts",
        tags=["data"],
        summary="All accounts as one nested blob (balances, txns, positions)",
    )
    def accounts(_session: Annotated[Session, Depends(get_session)]) -> dict[str, object]:
        return data.accounts_blob()

    return app


#: Module-level instance for ``uvicorn app.providers.legacy_bank.app:app``.
app = create_app()
