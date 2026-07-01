"""Mock OAuth2 for the FDX bank: token issuance, storage, and validation.

A deliberately small stand-in for the real thing. It models two grants:

* **client credentials** — the aggregator (a confidential client) authenticating
  machine-to-machine, kept as a runnable convenience.
* **authorization code + PKCE, initiated via PAR** (item-23) — the FAPI-shaped
  flow: the client pushes its request to ``/oauth2/par`` (with an ``S256``
  ``code_challenge``), exchanges the returned ``request_uri`` at
  ``/oauth2/authorize`` for a single-use code, and redeems that code at the token
  endpoint by proving it holds the matching ``code_verifier``. See the provider
  README for which slice of FAPI this covers and what stays out of scope.

The user-facing *consent* step a real flow would show lives in this project's own
consent layer (Items 7-8). Nothing here is a real secret — ``CLIENT_SECRET`` is a
fixed local value so the mock is runnable out of the box.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.security.pkce import s256_challenge

# --- Mock client + scopes ----------------------------------------------------

CLIENT_ID = "cdb-aggregator"
CLIENT_SECRET = "local-mock-secret"  # noqa: S105 - mock value, not a real credential

#: Scopes this provider understands. Each gates a slice of the resource API,
#: previewing the granular-permission theme the consent layer formalizes.
SUPPORTED_SCOPES: frozenset[str] = frozenset(
    {"accounts:read", "transactions:read", "customer:read"}
)

DEFAULT_TOKEN_TTL_SECONDS = 3600
PAR_TTL_SECONDS = 90  # a pushed request is short-lived (FAPI keeps this tight)
AUTH_CODE_TTL_SECONDS = 60  # authorization codes are single-use and short-lived


@dataclass(frozen=True)
class AccessToken:
    """An issued bearer token: its value, granted scopes, and expiry."""

    value: str
    scopes: frozenset[str]
    expires_at: datetime

    def is_expired(self, at: datetime | None = None) -> bool:
        return (at or datetime.now(UTC)) >= self.expires_at


@dataclass(frozen=True)
class PushedRequest:
    """A pushed authorization request (RFC 9126), awaiting ``/authorize``."""

    scopes: frozenset[str]
    code_challenge: str
    expires_at: datetime

    def is_expired(self, at: datetime | None = None) -> bool:
        return (at or datetime.now(UTC)) >= self.expires_at


@dataclass(frozen=True)
class AuthorizationCode:
    """A single-use authorization code bound to a PKCE ``code_challenge``."""

    scopes: frozenset[str]
    code_challenge: str
    expires_at: datetime

    def is_expired(self, at: datetime | None = None) -> bool:
        return (at or datetime.now(UTC)) >= self.expires_at


class TokenStore:
    """In-memory authorization-server state. One per app instance, so tests stay
    isolated: issued tokens, pushed authorization requests, and authorization codes."""

    def __init__(self) -> None:
        self._tokens: dict[str, AccessToken] = {}
        self._par: dict[str, PushedRequest] = {}
        self._codes: dict[str, AuthorizationCode] = {}

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

    # --- PAR + authorization-code (PKCE) -------------------------------------

    def push_request(self, scopes: frozenset[str], code_challenge: str) -> str:
        """Store a pushed authorization request; return its opaque ``request_uri``."""
        request_uri = f"urn:ietf:params:oauth:request_uri:{secrets.token_urlsafe(18)}"
        self._par[request_uri] = PushedRequest(
            scopes=scopes,
            code_challenge=code_challenge,
            expires_at=datetime.now(UTC) + timedelta(seconds=PAR_TTL_SECONDS),
        )
        return request_uri

    def consume_request(self, request_uri: str) -> PushedRequest | None:
        """Pop a pushed request (single use); return it, or ``None`` if absent/expired."""
        pushed = self._par.pop(request_uri, None)
        if pushed is None or pushed.is_expired():
            return None
        return pushed

    def issue_code(self, scopes: frozenset[str], code_challenge: str) -> str:
        """Mint a single-use authorization code bound to ``code_challenge``."""
        code = secrets.token_urlsafe(24)
        self._codes[code] = AuthorizationCode(
            scopes=scopes,
            code_challenge=code_challenge,
            expires_at=datetime.now(UTC) + timedelta(seconds=AUTH_CODE_TTL_SECONDS),
        )
        return code

    def redeem_code(self, code: str, code_verifier: str) -> AccessToken | None:
        """Redeem a code, proving PKCE. Returns a token, or ``None`` if the code is
        unknown/expired or the verifier doesn't match the bound challenge."""
        authorization = self._codes.pop(code, None)  # single use, even on failure
        if authorization is None or authorization.is_expired():
            return None
        if s256_challenge(code_verifier) != authorization.code_challenge:
            return None
        return self.issue(authorization.scopes)


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
