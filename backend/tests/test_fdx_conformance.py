"""FDX schema conformance (item-27).

Validates the mock FDX provider's *actual responses* against vendored FDX-subset
JSON Schemas, so a change that drifts from the FDX shape fails the build loudly.
The schemas are hand-authored (FDX's official schemas require membership) and
cover the entities this project models — see docs/fdx-conformance.md for exactly
which entities/fields are in scope and how the canonical model maps onto them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

import app.providers.mock_fdx_bank as provider_pkg
from app.providers.mock_fdx_bank.app import create_app
from app.providers.mock_fdx_bank.auth import CLIENT_ID, CLIENT_SECRET

API = "/fdx/v6"
SCHEMA_DIR = Path(provider_pkg.__file__).parent / "fdx_schemas"


def _validator(entity: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / f"{entity}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)  # the schema itself is well-formed
    return Draft202012Validator(schema)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _auth(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_provider_responses_conform_to_fdx_schemas(client: TestClient) -> None:
    auth = _auth(client)
    customer_v = _validator("customer")
    account_v = _validator("account")
    holding_v = _validator("holding")
    transaction_v = _validator("transaction")

    customer_v.validate(client.get(f"{API}/customers/current", headers=auth).json())

    accounts = client.get(f"{API}/accounts", headers=auth).json()["accounts"]
    assert accounts  # there is something to check
    for summary in accounts:
        account_v.validate(summary)  # the list-view summary conforms
        detail = client.get(f"{API}/accounts/{summary['accountId']}", headers=auth).json()
        account_v.validate(detail)  # ...and so does the detail
        for holding in detail.get("holdings", []):
            holding_v.validate(holding)
        txns = client.get(
            f"{API}/accounts/{summary['accountId']}/transactions", headers=auth
        ).json()
        for transaction in txns["transactions"]:
            transaction_v.validate(transaction)


def test_conformance_fails_loudly_on_drift() -> None:
    transaction_v = _validator("transaction")
    valid = {
        "transactionId": "t-1",
        "accountId": "a-1",
        "amount": 10.0,
        "debitCreditMemo": "DEBIT",
        "status": "POSTED",
        "transactionTimestamp": "2026-01-01T00:00:00Z",
    }
    transaction_v.validate(valid)  # baseline passes

    # A removed required field is caught...
    with pytest.raises(ValidationError):
        transaction_v.validate({k: v for k, v in valid.items() if k != "amount"})
    # ...as is an unexpected field (additionalProperties: false)...
    with pytest.raises(ValidationError):
        transaction_v.validate({**valid, "wireTransferId": "x"})
    # ...as is a wrong type / signed amount slipping in.
    with pytest.raises(ValidationError):
        transaction_v.validate({**valid, "amount": -10.0})
