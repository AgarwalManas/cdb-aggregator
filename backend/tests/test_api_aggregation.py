"""Tests for the aggregation API (Item 10).

Confirms the unified views merge across sources and — crucially — that consent
governs them: the mortgage balance (granted without BALANCES) is withheld and
excluded from net worth, and revoking a connection drops its data.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_merged_accounts_span_sources(client: TestClient) -> None:
    accounts = client.get("/api/accounts").json()
    ids = {a["accountId"] for a in accounts}
    assert ids == {"fdx-chq", "fdx-tfsa", "fdx-visa", "leg-sav", "old-mortgage"}
    labels = {a["accountId"]: a["sourceLabel"] for a in accounts}
    assert labels["leg-sav"] == "Legacy Bank"
    assert labels["old-mortgage"] == "OldBank (scraped)"


def test_mortgage_balance_is_withheld(client: TestClient) -> None:
    accounts = {a["accountId"]: a for a in client.get("/api/accounts").json()}
    mortgage = accounts["old-mortgage"]  # scraper connection lacks BALANCES
    assert mortgage["balanceShared"] is False
    assert mortgage["current"] is None
    # A shared one still has its balance.
    assert accounts["fdx-chq"]["balanceShared"] is True
    assert Decimal(accounts["fdx-chq"]["current"]) == Decimal("4210.55")


def test_merged_transactions_sorted_desc(client: TestClient) -> None:
    txns = client.get("/api/transactions").json()
    times = [t["occurredAt"] for t in txns]
    assert times == sorted(times, reverse=True)
    # Feed spans sources.
    assert {t["sourceLabel"] for t in txns} >= {"Mock FDX Bank", "Legacy Bank"}
    assert any(t["direction"] == "CREDIT" for t in txns)
    assert any(t["direction"] == "DEBIT" for t in txns)


def test_net_worth_excludes_unshared_balance(client: TestClient) -> None:
    nw = client.get("/api/net-worth").json()
    # Assets: chq 4210.55 + tfsa 11193.50 + savings 15800.00 = 31204.05
    assert Decimal(nw["assets"]) == Decimal("31204.05")
    # Liabilities: only the Visa (1875.40); the mortgage is excluded (no BALANCES).
    assert Decimal(nw["liabilities"]) == Decimal("1875.40")
    assert Decimal(nw["netWorth"]) == Decimal("29328.65")
    excluded_ids = {e["accountId"] for e in nw["excluded"]}
    assert excluded_ids == {"old-mortgage"}
    assert nw["excluded"][0]["reason"] == "Balance not shared"


def test_revoking_a_connection_drops_its_data(client: TestClient) -> None:
    # Revoke the legacy connection (con-2 covers leg-sav).
    connections = client.get("/api/connections").json()
    legacy = next(c for c in connections if c["sourceId"] == "legacy_bank")
    assert client.post(f"/api/connections/{legacy['connectionId']}/revoke").status_code == 200

    accounts = {a["accountId"] for a in client.get("/api/accounts").json()}
    assert "leg-sav" not in accounts  # gone from the merged view
    nw = client.get("/api/net-worth").json()
    assert Decimal(nw["assets"]) == Decimal("15404.05")  # savings no longer counted
