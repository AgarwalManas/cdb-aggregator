"""Mock legacy auth: a username/password login that returns an opaque session id.

Deliberately *not* OAuth2. Legacy systems often hand out a single session token
with no notion of scope — access is all-or-nothing. That contrast with the FDX
bank's granular scopes is itself part of what this source demonstrates: the
aggregator's own consent layer (Items 7-8) has to impose fine-grained control
that the upstream source never offered.

Credentials are fixed mock values so the provider runs out of the box.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

LEGACY_USER = "ada"
LEGACY_PASS = "hunter2"  # noqa: S105 - mock value, not a real credential

SESSION_TTL_SECONDS = 1800


@dataclass(frozen=True)
class Session:
    """An opaque session: its id and expiry. No scopes — legacy is all-or-nothing."""

    sid: str
    expires_at: datetime

    def is_expired(self, at: datetime | None = None) -> bool:
        return (at or datetime.now(UTC)) >= self.expires_at


class SessionStore:
    """In-memory session store, one per app instance (keeps tests isolated)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def open(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> Session:
        session = Session(
            sid=secrets.token_hex(16),
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
        self._sessions[session.sid] = session
        return session

    def validate(self, sid: str) -> Session | None:
        session = self._sessions.get(sid)
        if session is None:
            return None
        if session.is_expired():
            self._sessions.pop(sid, None)
            return None
        return session


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def get_session(
    store: Annotated[SessionStore, Depends(get_session_store)],
    x_session_id: Annotated[str | None, Header()] = None,
) -> Session:
    """Require a valid ``X-Session-Id`` header; 401 otherwise."""
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-Session-Id header",
        )
    session = store.validate(x_session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired session",
        )
    return session
