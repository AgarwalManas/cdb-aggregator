"""Cookie-session auth for the screen-scraping mock.

The crux of the "old way": the user hands their **real banking username and
password** to a form. There's no token, no scope, no consent record — just a
session cookie, exactly like a human logging in. That's precisely what an
aggregator has to imitate to scrape, and precisely what FDX/open-banking exists
to replace.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status

OLDBANK_USER = "ada"
OLDBANK_PASS = "hunter2"  # noqa: S105 - mock value, not a real credential

COOKIE_NAME = "oldbank_session"
SESSION_TTL_SECONDS = 1800


@dataclass(frozen=True)
class Session:
    sid: str
    expires_at: datetime

    def is_expired(self, at: datetime | None = None) -> bool:
        return (at or datetime.now(UTC)) >= self.expires_at


class SessionStore:
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


def require_session(
    store: Annotated[SessionStore, Depends(get_session_store)],
    oldbank_session: Annotated[str | None, Cookie()] = None,
) -> Session:
    """Require a valid session cookie; 401 otherwise."""
    session = store.validate(oldbank_session) if oldbank_session else None
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not signed in",
        )
    return session
