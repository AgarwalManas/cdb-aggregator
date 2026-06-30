"""Tests for the mock FDX bank (Item 3): OAuth2 flow + FDX resource endpoints.

These cover the token endpoint's happy path and error bodies, the bearer/scope
gate on resources, and the FDX shape of the payloads. A final test maps a
provider account into the canonical model (Item 2) to prove the two are aligned
before the real adapter is written in Item 5.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models import Account, Balance
from app.providers.mock_fdx_bank.app import create_app
from app.providers.mock_fdx_bank.auth import CLIENT_ID, CLIENT_SECRET

API = "/fdx/v6"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _token(client: TestClient, scope: str | None = None) -> str:
    form = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    if scope is not None:
        form["scope"] = scope
    resp = client.post("/oauth2/token", data=form)
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- OAuth2 token endpoint ---------------------------------------------------


def test_token_happy_path_grants_all_scopes_by_default() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0
    # No scope requested -> all supported scopes granted.
    assert "accounts:read" in body["scope"].split()


def test_token_rejects_bad_client() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": "wrong",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_client"


def test_token_rejects_unsupported_grant_type() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/oauth2/token",
        data={"grant_type": "password", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "unsupported_grant_type"


def test_token_rejects_unknown_scope() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "accounts:read wire:transfer",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_scope"


# --- Bearer + scope enforcement ----------------------------------------------


def test_resource_requires_token(client: TestClient) -> None:
    resp = client.get(f"{API}/accounts")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"].startswith("Bearer")


def test_resource_rejects_invalid_token(client: TestClient) -> None:
    resp = client.get(f"{API}/accounts", headers=_auth("not-a-real-token"))
    assert resp.status_code == 401
    assert 'error="invalid_token"' in resp.headers["www-authenticate"]


def test_scope_is_enforced(client: TestClient) -> None:
    # A token scoped only for customer:read may not list accounts.
    token = _token(client, scope="customer:read")
    resp = client.get(f"{API}/accounts", headers=_auth(token))
    assert resp.status_code == 403
    assert 'error="insufficient_scope"' in resp.headers["www-authenticate"]
    # ...but it can read the customer.
    assert client.get(f"{API}/customers/current", headers=_auth(token)).status_code == 200


# --- FDX resource shapes -----------------------------------------------------


def test_list_accounts_returns_summaries_without_holdings(client: TestClient) -> None:
    token = _token(client, scope="accounts:read")
    resp = client.get(f"{API}/accounts", headers=_auth(token))
    assert resp.status_code == 200
    accounts = resp.json()["accounts"]
    assert {a["accountId"] for a in accounts} == {"acc-chq-001", "acc-sav-001", "acc-inv-001"}
    # Summaries omit holdings; currency is an FDX object.
    for a in accounts:
        assert "holdings" not in a
        assert a["currency"]["currencyCode"] == "CAD"


def test_account_detail_includes_balances_and_holdings(client: TestClient) -> None:
    token = _token(client)
    resp = client.get(f"{API}/accounts/acc-inv-001", headers=_auth(token))
    assert resp.status_code == 200
    account = resp.json()
    assert account["currentBalance"] == 11193.50
    symbols = {h["symbol"] for h in account["holdings"]}
    assert "VFV" in symbols  # an ETF holding
    assert any(h["holdingType"] == "CASH" for h in account["holdings"])


def test_unknown_account_is_404(client: TestClient) -> None:
    token = _token(client)
    resp = client.get(f"{API}/accounts/does-not-exist", headers=_auth(token))
    assert resp.status_code == 404
    assert resp.json()["error"] == "not_found"


def test_transactions_use_fdx_amount_convention(client: TestClient) -> None:
    token = _token(client, scope="transactions:read")
    resp = client.get(f"{API}/accounts/acc-chq-001/transactions", headers=_auth(token))
    assert resp.status_code == 200
    txns = resp.json()["transactions"]
    # Unsigned amount + debitCreditMemo direction.
    assert all(t["amount"] > 0 for t in txns)
    assert {t["debitCreditMemo"] for t in txns} <= {"DEBIT", "CREDIT"}
    # The pending transaction carries no postedTimestamp.
    pending = [t for t in txns if t["status"] == "PENDING"]
    assert pending and "postedTimestamp" not in pending[0]


def test_customer_endpoint(client: TestClient) -> None:
    token = _token(client, scope="customer:read")
    resp = client.get(f"{API}/customers/current", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["customerId"] == "cust-001"


# --- Alignment with the canonical model (Item 2) -----------------------------


def test_fdx_account_maps_cleanly_into_canonical_model(client: TestClient) -> None:
    """The clean source should require only a trivial mapping into canonical types.

    This previews — and sanity-checks — the Item 5 adapter: pull the FDX account,
    translate field names, and the canonical model accepts it.
    """

    token = _token(client)
    fdx = client.get(f"{API}/accounts/acc-chq-001", headers=_auth(token)).json()

    canonical = Account(
        account_id=fdx["accountId"],
        customer_id=fdx["customerId"],
        category=fdx["accountCategory"],
        account_type=fdx["accountType"],
        status=fdx["status"],
        currency=fdx["currency"]["currencyCode"],
        masked_number=fdx["maskedAccountNumber"],
        balances=[
            Balance(
                as_of=datetime.fromisoformat(fdx["balanceAsOf"].replace("Z", "+00:00")),
                currency=fdx["currency"]["currencyCode"],
                current=Decimal(str(fdx["currentBalance"])),
                available=Decimal(str(fdx["availableBalance"])),
                balance_type=fdx["balanceType"],
            )
        ],
    )
    assert canonical.account_id == "acc-chq-001"
    assert canonical.balances[0].current == Decimal("4210.55")
