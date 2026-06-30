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

from . import data
from .auth import (
    CLIENT_ID,
    CLIENT_SECRET,
    DEFAULT_TOKEN_TTL_SECONDS,
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
            "tokenEndpoint": "/oauth2/token",
            "resourceBasePath": _API,
            "docs": "/docs",
        }

    # --- OAuth2 token endpoint ------------------------------------------------

    @app.post("/oauth2/token", tags=["oauth2"], summary="Issue an access token")
    def issue_token(
        request: Request,
        grant_type: str = Form(...),
        client_id: str = Form(...),
        client_secret: str = Form(...),
        scope: str | None = Form(default=None),
    ) -> JSONResponse:
        """Client-credentials grant. Returns a bearer token scoped as requested."""

        if grant_type != "client_credentials":
            return _oauth_error(
                "unsupported_grant_type",
                "only client_credentials is supported by this mock",
            )
        if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
            return _oauth_error("invalid_client", "unknown client credentials", 401)

        # No scope requested -> grant everything this provider supports.
        requested = frozenset(scope.split()) if scope else SUPPORTED_SCOPES
        unknown = requested - SUPPORTED_SCOPES
        if unknown:
            return _oauth_error(
                "invalid_scope", f"unsupported scope(s): {', '.join(sorted(unknown))}"
            )

        token = request.app.state.token_store.issue(requested)
        return JSONResponse(
            {
                "access_token": token.value,
                "token_type": "Bearer",
                "expires_in": DEFAULT_TOKEN_TTL_SECONDS,
                "scope": " ".join(sorted(token.scopes)),
            }
        )

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
