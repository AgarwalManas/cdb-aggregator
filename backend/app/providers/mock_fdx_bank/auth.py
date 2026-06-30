"""Mock OAuth2 for the FDX bank: token issuance, storage, and validation.

A deliberately small stand-in for the real thing. It models the *client
credentials* grant — the aggregator (a confidential client) authenticating to
the bank machine-to-machine — which is enough to demonstrate token-based,
scoped, expiring access without a browser redirect flow. A production FDX
integration would use the authorization-code grant with PKCE under a FAPI
security profile and a real user-consent step; that user-facing consent is
modeled separately in this project's own consent layer (Items 7-8).

Nothing here is a real secret. ``CLIENT_SECRET`` is a fixed local value so the
mock is runnable out of the box.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

# --- Mock client + scopes ----------------------------------------------------

CLIENT_ID = "cdb-aggregator"
CLIENT_SECRET = "local-mock-secret"  # noqa: S105 - mock value, not a real credential

#: Scopes this provider understands. Each gates a slice of the resource API,
#: previewing the granular-permission theme the consent layer formalizes.
SUPPORTED_SCOPES: frozenset[str] = frozenset(
    {"accounts:read", "transactions:read", "customer:read"}
)

DEFAULT_TOKEN_TTL_SECONDS = 3600


@dataclass(frozen=True)
class AccessToken:
    """An issued bearer token: its value, granted scopes, and expiry."""

    value: str
    scopes: frozenset[str]
    expires_at: datetime

    def is_expired(self, at: datetime | None = None) -> bool:
        return (at or datetime.now(UTC)) >= self.expires_at


class TokenStore:
    """In-memory token store. One per app instance, so tests stay isolated."""

    def __init__(self) -> None:
        self._tokens: dict[str, AccessToken] = {}

    def issue(
        self, scopes: frozenset[str], ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS
    ) -> AccessToken:
        token = AccessToken(
            value=secrets.token_urlsafe(24),
            scopes=scopes,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
        self._tokens[token.value] = token
        return token

    def validate(self, raw_value: str) -> AccessToken | None:
        """Return the live token for ``raw_value``, or ``None`` if absent/expired."""
        token = self._tokens.get(raw_value)
        if token is None:
            return None
        if token.is_expired():
            self._tokens.pop(raw_value, None)  # lazy cleanup
            return None
        return token


# --- FastAPI dependencies ----------------------------------------------------


def get_token_store(request: Request) -> TokenStore:
    """The store lives on app state so each ``create_app()`` is independent."""
    return request.app.state.token_store


def get_current_token(
    store: Annotated[TokenStore, Depends(get_token_store)],
    authorization: Annotated[str | None, Header()] = None,
) -> AccessToken:
    """Resolve and validate the bearer token on the request.

    Raises 401 (with a ``WWW-Authenticate`` header, per RFC 6750) when the token
    is missing, malformed, unknown, or expired.
    """

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = store.validate(authorization.split(" ", 1)[1].strip())
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired access token",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    return token


def require_scopes(*needed: str):
    """Build a dependency that requires ``needed`` scopes on the token.

    Returns 403 (``insufficient_scope``) when the token is valid but lacks a
    required scope — the standard OAuth2 distinction from a 401.
    """

    required = frozenset(needed)

    def dependency(token: Annotated[AccessToken, Depends(get_current_token)]) -> AccessToken:
        if not required.issubset(token.scopes):
            missing = ", ".join(sorted(required - token.scopes))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"insufficient_scope: missing {missing}",
                headers={"WWW-Authenticate": 'Bearer error="insufficient_scope"'},
            )
        return token

    return dependency
