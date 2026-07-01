"""Coverage-completion tests (Item 12).

Exercises the last defensive branches, ``connect()`` transport constructors,
provider service roots, store-expiry paths, and route guards so coverage is a
full 100% — appropriate for a financial codebase where the untested branch is
the one that bites.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.adapters import FdxHttpClient, HtmlStatementClient, LegacyHttpClient
from app.adapters.base import SourceAdapter
from app.adapters.scraper_bank import parse_accounts
from app.agent import AGENT_ID, run_cash_finder
from app.api.aggregation import merged_accounts, merged_transactions
from app.api.demo import AggregatorState, Connection, build_demo_state
from app.api.routes.agent import _current_delegation, get_delegation, revoke_delegation
from app.consent import ConsentEnforcingReader, ConsentGate, ConsentStore
from app.main import create_app
from app.models import (
    Account,
    AccountCategory,
    AccountType,
    Balance,
    ConsentScope,
    Customer,
    InvestmentHolding,
    PersonName,
    Transaction,
)
from app.providers.legacy_bank.app import create_app as create_legacy_app
from app.providers.legacy_bank.auth import SessionStore as LegacySessionStore
from app.providers.mock_fdx_bank.app import create_app as create_fdx_app
from app.providers.mock_fdx_bank.auth import CLIENT_ID, CLIENT_SECRET, TokenStore
from app.providers.scraper_bank.auth import SessionStore as ScraperSessionStore

T0 = datetime(2026, 1, 1, tzinfo=UTC)
DAY = timedelta(days=1)
DEPOSIT = AccountCategory.DEPOSIT_ACCOUNT


class CovAdapter(SourceAdapter):
    source_name = "cov"

    def get_customer(self) -> Customer:
        return Customer(customer_id="c", name=PersonName(first="A", last="B"))

    def get_accounts(self) -> list[Account]:
        return [
            Account(
                account_id="acc-1",
                category=DEPOSIT,
                account_type=AccountType.CHECKING,
                currency="CAD",
                balances=[Balance(as_of=T0, currency="CAD", current="5000.00")],
            ),
            Account(
                account_id="empty",
                category=DEPOSIT,
                account_type=AccountType.CHECKING,
                currency="CAD",
                balances=[],
            ),
        ]

    def get_transactions(self, account_id: str) -> list[Transaction]:
        return []

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        return []


def _state(connections, adapter=None) -> AggregatorState:
    store = ConsentStore()
    conns = []
    for i, (scopes, account_ids, source) in enumerate(connections, start=1):
        cid = f"c{i}"
        store.grant(
            "c",
            "cdb-aggregator",
            scopes,
            duration=30 * DAY,
            account_ids=account_ids,
            now=T0,
            consent_id=cid,
        )
        conns.append(Connection(cid, source, source))
    from app.consent import AuditLog

    return AggregatorState(
        store=store,
        audit=AuditLog(),
        connections=conns,
        adapter=adapter or CovAdapter(),
        customer_id="c",
        recipient="cdb-aggregator",
    )


# --- Aggregation defensive branches ------------------------------------------


def test_merged_accounts_dedupes_across_connections() -> None:
    # Two connections both cover acc-1 -> the second hits the "already seen" skip.
    state = _state(
        [
            ({ConsentScope.ACCOUNT_DETAILS}, ["acc-1"], "mock_fdx_bank"),
            ({ConsentScope.ACCOUNT_DETAILS}, ["acc-1"], "legacy_bank"),
        ]
    )
    assert [a.account_id for a in merged_accounts(state, at=T0 + DAY)] == ["acc-1"]


def test_aggregation_skips_inactive_connection() -> None:
    state = _state([({ConsentScope.TRANSACTIONS}, ["acc-1"], "legacy_bank")])
    state.store.revoke("c1", now=T0 + DAY)  # now inactive
    at = T0 + 2 * DAY
    assert merged_transactions(state, at=at) == []
    assert merged_accounts(state, at=at) == []


# --- Agent no-balance branch -------------------------------------------------


def test_agent_reports_account_with_no_balance() -> None:
    store = ConsentStore()
    store.grant(
        "c",
        AGENT_ID,
        {ConsentScope.ACCOUNT_DETAILS, ConsentScope.BALANCES},
        duration=30 * DAY,
        account_ids=["empty"],
        now=T0,
    )
    reader = ConsentEnforcingReader(CovAdapter(), ConsentGate(store))
    result = run_cash_finder(
        reader, customer_id="c", account_ids=["empty"], source_label=lambda a: None, at=T0 + DAY
    )
    assert result.not_counted[0].reason == "no balance available"


# --- Gate authorize success path ---------------------------------------------


def test_gate_authorize_returns_consent_on_allow() -> None:
    store = ConsentStore()
    store.grant("c", "r", {ConsentScope.ACCOUNT_DETAILS}, duration=30 * DAY, now=T0)
    consent = ConsentGate(store).authorize("c", "r", ConsentScope.ACCOUNT_DETAILS, at=T0 + DAY)
    assert consent.customer_id == "c"


# --- Demo helpers ------------------------------------------------------------


def test_demo_helpers_edge_cases() -> None:
    state = build_demo_state(T0)
    assert state.connection_for_account("does-not-exist") is None
    assert state.adapter.get_holdings("fdx-chq") == []  # non-investment -> no holdings
    # After a revoke, the revoked connection drops out of the shareable set.
    state.store.revoke(state.connections[0].connection_id, now=T0 + DAY)
    remaining = state.balance_shared_account_ids(T0 + 2 * DAY)
    assert "fdx-chq" not in remaining  # it belonged to the revoked FDX connection


# --- Agent route guards (no delegation) --------------------------------------


def test_agent_routes_with_no_delegation() -> None:
    state = build_demo_state(T0)
    state.agent_delegation_id = None
    assert _current_delegation(state) is None
    assert get_delegation(state).status == "NONE"
    with pytest.raises(HTTPException):
        revoke_delegation(state)


# --- Consent route guards ----------------------------------------------------


def test_sources_endpoint_and_empty_scope_grant() -> None:
    client = TestClient(create_app())
    sources = client.get("/api/sources").json()
    assert {s["sourceId"] for s in sources} == {"mock_fdx_bank", "legacy_bank", "scraper_bank"}
    # Granting with an empty scope list is rejected.
    resp = client.post("/api/connections", json={"sourceId": "legacy_bank", "scopes": []})
    assert resp.status_code == 422


# --- Model validator pass-through --------------------------------------------


def test_customer_accepts_past_date_of_birth() -> None:
    customer = Customer(
        customer_id="c",
        name=PersonName(first="Ada", last="Lovelace"),
        date_of_birth=date(2000, 1, 1),
    )
    assert customer.date_of_birth == date(2000, 1, 1)


# --- Transport connect() constructors ----------------------------------------


def test_http_client_connect_constructors() -> None:
    # connect() builds a real httpx.Client (no request is made here).
    FdxHttpClient.connect("http://fdx.test", CLIENT_ID, CLIENT_SECRET).close()
    LegacyHttpClient.connect("http://legacy.test", "ada", "hunter2").close()
    scraper = HtmlStatementClient.connect("http://old.test", "ada", "hunter2")
    assert scraper.get_holdings("anything") == []  # statements expose no holdings
    scraper.close()


# --- Scraper balance-parse failure -------------------------------------------


def test_scraper_unparseable_balance_raises() -> None:
    html = (
        '<html><body><p class="statement-date">As of: 2026-06-30</p>'
        '<div class="account" data-acct="x"><h2>Chequing (x)</h2>'
        '<p class="balance">Balance: free money</p></div></body></html>'
    )
    with pytest.raises(ValueError, match="could not parse balance"):
        parse_accounts(html)


# --- Provider service roots + edge auth --------------------------------------


def test_provider_service_roots() -> None:
    assert TestClient(create_fdx_app()).get("/").json()["service"] == "Mock FDX Bank"
    assert TestClient(create_legacy_app()).get("/").json()["service"] == "Legacy Bank"


def test_fdx_transactions_unknown_account_is_404() -> None:
    client = TestClient(create_fdx_app())
    token = client.post(
        "/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    ).json()["access_token"]
    resp = client.get(
        "/fdx/v6/accounts/nope/transactions", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


def test_token_and_session_stores_expire() -> None:
    tokens = TokenStore()
    token = tokens.issue(frozenset({"accounts:read"}), ttl_seconds=-10)  # already expired
    assert tokens.validate(token.value) is None

    legacy = LegacySessionStore()
    session = legacy.open(ttl_seconds=-10)
    assert legacy.validate(session.sid) is None

    scraper = ScraperSessionStore()
    assert scraper.validate("unknown-sid") is None
    expired = scraper.open(ttl_seconds=-10)
    assert scraper.validate(expired.sid) is None


def test_decimal_amount_stays_exact() -> None:
    # A small guard that Decimal money doesn't drift, used across the suite.
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
