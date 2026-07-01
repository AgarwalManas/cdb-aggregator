"""Tests for selective-disclosure attestations (item-32, simulated).

The engine proves a derived fact and signs *only the conclusion*, so the tests
check both that the maths is right (each fact, both ways) and that the
attestation is tamper-evident: a valid issue verifies, and altering any signed
field fails verification. It is a simulation — a symmetric HMAC stands in for a
real ZK proof — but the signing/verification round-trip must still hold.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.attestation import FACTS, compute, issue, verify
from app.main import create_app
from app.models import Account, AccountCategory, AccountType, Balance, BalanceType

T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _acct(current: str, *, balance_type: BalanceType = BalanceType.ASSET) -> Account:
    return Account(
        account_id="a",
        customer_id="c",
        category=AccountCategory.DEPOSIT_ACCOUNT,
        account_type=AccountType.CHECKING,
        currency="CAD",
        balances=[Balance(as_of=T0, currency="CAD", current=current, balance_type=balance_type)],
    )


# --- API ---------------------------------------------------------------------


def test_catalog_lists_provable_facts(client: TestClient) -> None:
    catalog = client.get("/api/attestations/catalog").json()
    assert {f["factId"] for f in catalog} == set(FACTS)
    assert all(f["disclosure"] for f in catalog)  # each states what stays hidden


def test_issue_then_verify_round_trip(client: TestClient) -> None:
    att = client.post("/api/attestations/issue", json={"factId": "liquid_10k"}).json()
    assert att["holds"] is True  # the seeded world clears the threshold
    assert att["simulated"] is True
    assert att["signature"]
    result = client.post("/api/attestations/verify", json={"attestation": att}).json()
    assert result["valid"] is True


def test_altering_the_conclusion_fails_verification(client: TestClient) -> None:
    att = client.post("/api/attestations/issue", json={"factId": "liquid_10k"}).json()
    att["holds"] = False  # flip the signed conclusion
    result = client.post("/api/attestations/verify", json={"attestation": att}).json()
    assert result["valid"] is False
    assert "altered" in result["reason"].lower()


def test_issue_unknown_fact_is_404(client: TestClient) -> None:
    assert client.post("/api/attestations/issue", json={"factId": "nope"}).status_code == 404


# --- Engine branches ---------------------------------------------------------


def test_compute_covers_every_fact_both_ways() -> None:
    rich = [_acct("9000"), _acct("2000")]  # 11,000 total, all non-negative
    poor = [_acct("100"), _acct("-50")]  # 50 total, one overdrawn
    assert compute("liquid_10k", rich, has_income=True) is True
    assert compute("liquid_10k", poor, has_income=True) is False
    assert compute("no_overdraft", rich, has_income=True) is True
    assert compute("no_overdraft", poor, has_income=True) is False
    assert compute("salary_here", rich, has_income=True) is True
    assert compute("salary_here", rich, has_income=False) is False


def test_a_false_fact_is_still_a_valid_signed_attestation() -> None:
    att = issue("liquid_10k", subject="c", accounts=[_acct("5")], has_income=False, now=T0)
    assert att["holds"] is False
    assert att["claim"] == FACTS["liquid_10k"].claim_false
    ok, _ = verify(att)
    assert ok is True  # "false" is a legitimate, signed conclusion


def test_verify_rejects_an_attestation_with_no_signature() -> None:
    ok, reason = verify({"fact_id": "liquid_10k"})
    assert ok is False
    assert "signature" in reason.lower()
