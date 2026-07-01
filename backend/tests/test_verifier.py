"""Tests for the verifiable-presentation / wallet flow (item-33, simulated).

The holder presents a *selected* subset of signed attestations to a verifier,
which checks each signature and its policy and returns accept/reject. The tests
cover the four ways a requirement can land — satisfied, fact-doesn't-hold,
bad-signature, not-presented — plus the accept/reject decision and the API.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.attestation import issue
from app.main import create_app
from app.models import Account, AccountCategory, AccountType, Balance, BalanceType
from app.verifier import present

T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _acct(current: str) -> Account:
    return Account(
        account_id="a",
        customer_id="c",
        category=AccountCategory.DEPOSIT_ACCOUNT,
        account_type=AccountType.CHECKING,
        currency="CAD",
        balances=[
            Balance(as_of=T0, currency="CAD", current=current, balance_type=BalanceType.ASSET)
        ],
    )


RICH = [_acct("11000")]
POOR = [_acct("5")]


def _att(fact_id: str, accounts: list[Account], *, has_income: bool = True) -> dict:
    return issue(fact_id, subject="c", accounts=accounts, has_income=has_income, now=T0)


def _result(outcome: dict, fact_id: str) -> dict:
    return next(r for r in outcome["results"] if r["fact_id"] == fact_id)


# --- present() branches ------------------------------------------------------


def test_present_accepts_when_every_requirement_is_met() -> None:
    outcome = present("rental", [_att("liquid_10k", RICH), _att("no_overdraft", RICH)])
    assert outcome["accepted"] is True
    assert all(r["satisfied"] for r in outcome["results"])


def test_missing_credential_is_not_presented() -> None:
    outcome = present("rental", [_att("liquid_10k", RICH)])
    assert outcome["accepted"] is False
    assert _result(outcome, "no_overdraft")["detail"] == "Not presented."


def test_credential_whose_fact_does_not_hold_is_rejected() -> None:
    # liquid_10k is validly signed but holds False (poor) — the verifier needs True.
    outcome = present("rental", [_att("liquid_10k", POOR), _att("no_overdraft", RICH)])
    assert outcome["accepted"] is False
    assert "does not hold" in _result(outcome, "liquid_10k")["detail"]


def test_tampered_credential_fails_on_signature() -> None:
    good = _att("liquid_10k", RICH)
    tampered = {**good, "holds": not good["holds"]}  # flipping a signed field breaks the MAC
    outcome = present("rental", [tampered, _att("no_overdraft", RICH)])
    assert outcome["accepted"] is False
    assert "signature" in _result(outcome, "liquid_10k")["detail"].lower()


# --- API ---------------------------------------------------------------------


def test_verifiers_catalog_lists_requirements(client: TestClient) -> None:
    verifiers = client.get("/api/attestations/verifiers").json()
    ids = {v["verifierId"] for v in verifiers}
    assert ids == {"rental", "lender"}
    assert all(v["requirements"] for v in verifiers)


def test_present_endpoint_accepts_a_complete_presentation(client: TestClient) -> None:
    a1 = client.post("/api/attestations/issue", json={"factId": "liquid_10k"}).json()
    a2 = client.post("/api/attestations/issue", json={"factId": "no_overdraft"}).json()
    result = client.post(
        "/api/attestations/present",
        json={"verifierId": "rental", "attestations": [a1, a2]},
    ).json()
    assert result["accepted"] is True
    assert result["presentedCount"] == 2
    assert result["verifierName"] == "Rental application (demo)"


def test_present_endpoint_rejects_a_partial_presentation(client: TestClient) -> None:
    a1 = client.post("/api/attestations/issue", json={"factId": "liquid_10k"}).json()
    result = client.post(
        "/api/attestations/present",
        json={"verifierId": "rental", "attestations": [a1]},
    ).json()
    assert result["accepted"] is False


def test_present_unknown_verifier_is_404(client: TestClient) -> None:
    assert (
        client.post(
            "/api/attestations/present", json={"verifierId": "nope", "attestations": []}
        ).status_code
        == 404
    )
