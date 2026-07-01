"""The mock FDX bank's FastAPI application.

Endpoints:

* ``POST /oauth2/token`` — OAuth2 client-credentials token endpoint.
* ``GET  /fdx/v6/customers/current`` — the authenticated customer.
* ``GET  /fdx/v6/accounts`` — account summaries.
* ``GET  /fdx/v6/accounts/{id}`` — account detail (balances; holdings if any).
* ``GET  /fdx/v6/accounts/{id}/transactions`` — the account's transactions.

Resource endpoints are gated by bearer token + scope. The token endpoint speaks
OAuth2 error bodies (``{"error": ...}``) rather than FastAPI's default
``{"detail": ...}`` so it reads like a real authorization server.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import JSONResponse

from app.security.pkce import CODE_CHALLENGE_METHOD

from . import data
from .auth import (
    CLIENT_ID,
    CLIENT_SECRET,
    DEFAULT_TOKEN_TTL_SECONDS,
    PAR_TTL_SECONDS,
    SUPPORTED_SCOPES,
    TokenStore,
    require_scopes,
)

_API = f"/fdx/{data.FDX_API_VERSION}"


def _oauth_error(error: str, description: str, status_code: int = 400) -> JSONResponse:
    """An RFC 6749 §5.2 error response."""
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "error_description": description},
    )


def create_app() -> FastAPI:
    """Construct the mock bank app with its own isolated token store."""

    app = FastAPI(
        title="Mock FDX Bank",
        version="1.0.0",
        summary="A standalone mock FDX data provider: OAuth2 + FDX-shaped JSON.",
    )
    app.state.token_store = TokenStore()

    @app.get("/", tags=["meta"], summary="Service root")
    def root() -> dict[str, object]:
        return {
            "service": "Mock FDX Bank",
            "fdxVersion": data.FDX_API_VERSION,
            "pushedAuthorizationRequestEndpoint": "/oauth2/par",
            "authorizationEndpoint": "/oauth2/authorize",
            "tokenEndpoint": "/oauth2/token",
            "resourceBasePath": _API,
            "docs": "/docs",
        }

    # --- OAuth2: PAR + authorization-code (PKCE) + token ----------------------

    def _token_response(token: object) -> JSONResponse:
        return JSONResponse(
            {
                "access_token": token.value,
                "token_type": "Bearer",
                "expires_in": DEFAULT_TOKEN_TTL_SECONDS,
                "scope": " ".join(sorted(token.scopes)),
            }
        )

    def _resolve_scopes(scope: str | None) -> frozenset[str] | JSONResponse:
        """No scope requested -> everything supported; otherwise validate the set."""
        requested = frozenset(scope.split()) if scope else SUPPORTED_SCOPES
        unknown = requested - SUPPORTED_SCOPES
        if unknown:
            return _oauth_error(
                "invalid_scope", f"unsupported scope(s): {', '.join(sorted(unknown))}"
            )
        return requested

    @app.post("/oauth2/par", tags=["oauth2"], summary="Pushed authorization request (RFC 9126)")
    def pushed_authorization_request(
        request: Request,
        client_id: str = Form(...),
        client_secret: str = Form(...),
        code_challenge: str = Form(...),
        code_challenge_method: str = Form(...),
        scope: str | None = Form(default=None),
    ) -> JSONResponse:
        """Push the authorization request up front; return an opaque ``request_uri``."""
        if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
            return _oauth_error("invalid_client", "unknown client credentials", 401)
        if code_challenge_method != CODE_CHALLENGE_METHOD:
            return _oauth_error(
                "invalid_request", f"code_challenge_method must be {CODE_CHALLENGE_METHOD}"
            )
        scopes = _resolve_scopes(scope)
        if isinstance(scopes, JSONResponse):
            return scopes
        request_uri = request.app.state.token_store.push_request(scopes, code_challenge)
        return JSONResponse(
            status_code=201, content={"request_uri": request_uri, "expires_in": PAR_TTL_SECONDS}
        )

    @app.get("/oauth2/authorize", tags=["oauth2"], summary="Authorize a pushed request")
    def authorize(request: Request, client_id: str, request_uri: str) -> JSONResponse:
        """Exchange a pushed ``request_uri`` for a single-use authorization code.

        A browser flow would 302 to the redirect URI with ``?code=…``; the mock
        returns the code as JSON since there is no user agent.
        """
        if client_id != CLIENT_ID:
            return _oauth_error("invalid_client", "unknown client", 401)
        pushed = request.app.state.token_store.consume_request(request_uri)
        if pushed is None:
            return _oauth_error("invalid_request", "unknown or expired request_uri")
        code = request.app.state.token_store.issue_code(pushed.scopes, pushed.code_challenge)
        return JSONResponse({"code": code})

    @app.post("/oauth2/token", tags=["oauth2"], summary="Issue an access token")
    def issue_token(
        request: Request,
        grant_type: str = Form(...),
        client_id: str = Form(...),
        client_secret: str = Form(...),
        scope: str | None = Form(default=None),
        code: str | None = Form(default=None),
        code_verifier: str | None = Form(default=None),
    ) -> JSONResponse:
        """``client_credentials`` or ``authorization_code`` (with PKCE) grant."""
        if grant_type not in ("client_credentials", "authorization_code"):
            return _oauth_error(
                "unsupported_grant_type",
                "only client_credentials and authorization_code are supported by this mock",
            )
        if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
            return _oauth_error("invalid_client", "unknown client credentials", 401)

        store = request.app.state.token_store
        if grant_type == "authorization_code":
            if not code or not code_verifier:
                return _oauth_error(
                    "invalid_request", "authorization_code grant requires code and code_verifier"
                )
            token = store.redeem_code(code, code_verifier)
            if token is None:
                return _oauth_error(
                    "invalid_grant", "code is invalid/expired or PKCE verification failed"
                )
            return _token_response(token)

        scopes = _resolve_scopes(scope)
        if isinstance(scopes, JSONResponse):
            return scopes
        return _token_response(store.issue(scopes))

    # --- FDX resource endpoints ----------------------------------------------

    @app.get(
        f"{_API}/customers/current",
        tags=["fdx"],
        summary="The authenticated customer",
        dependencies=[Depends(require_scopes("customer:read"))],
    )
    def get_customer() -> dict[str, object]:
        return data.CUSTOMER

    @app.get(
        f"{_API}/accounts",
        tags=["fdx"],
        summary="List account summaries",
        dependencies=[Depends(require_scopes("accounts:read"))],
    )
    def list_accounts() -> dict[str, object]:
        accounts = [data.account_summary(a) for a in data.ACCOUNTS.values()]
        return {"accounts": accounts, "page": {"totalElements": len(accounts), "nextOffset": None}}

    @app.get(
        f"{_API}/accounts/{{account_id}}",
        tags=["fdx"],
        summary="Account detail (balances, and holdings if investment)",
        dependencies=[Depends(require_scopes("accounts:read"))],
        response_model=None,  # may return a JSONResponse (404) or the account dict
    )
    def get_account(account_id: str) -> JSONResponse | dict[str, object]:
        account = data.ACCOUNTS.get(account_id)
        if account is None:
            return _account_not_found(account_id)
        return account

    @app.get(
        f"{_API}/accounts/{{account_id}}/transactions",
        tags=["fdx"],
        summary="Transactions for an account",
        dependencies=[Depends(require_scopes("transactions:read"))],
        response_model=None,  # may return a JSONResponse (404) or the transactions dict
    )
    def get_transactions(account_id: str) -> JSONResponse | dict[str, object]:
        if account_id not in data.ACCOUNTS:
            return _account_not_found(account_id)
        txns = data.TRANSACTIONS.get(account_id, [])
        return {"transactions": txns, "page": {"totalElements": len(txns), "nextOffset": None}}

    return app


def _account_not_found(account_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "error_description": f"no account {account_id!r}"},
    )


#: Module-level instance for ``uvicorn app.providers.mock_fdx_bank.app:app``.
app = create_app()
