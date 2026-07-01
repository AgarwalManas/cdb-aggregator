"""Tests for the agentic delegation / intent layer (Item 11).

The engine's arithmetic matters, but the point is governance: the agent is bound
by the same consent gate as anything else. It reads only what's delegated, its
access is logged against the *agent* identity, and with no active delegation it
can't act at all.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.adapters.base import SourceAdapter
from app.agent import AGENT_ID, REQUIRED_SCOPES, run_cash_finder
from app.agent.cash_finder import TARGET_RATE
from app.consent import (
    AuditLog,
    ConsentEnforcingReader,
    ConsentGate,
    ConsentStore,
)
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

CUSTOMER = "cust-1"
T0 = datetime(2026, 1, 1, tzinfo=UTC)
DAY = timedelta(days=1)


def _acct(account_id, atype, current, category=AccountCategory.DEPOSIT_ACCOUNT) -> Account:
    return Account(
        account_id=account_id,
        customer_id=CUSTOMER,
        category=category,
        account_type=atype,
        currency="CAD",
        balances=[Balance(as_of=T0, currency="CAD", current=current)],
    )


class StubAdapter(SourceAdapter):
    source_name = "stub"

    def get_customer(self) -> Customer:
        return Customer(customer_id=CUSTOMER, name=PersonName(first="Ada", last="Lovelace"))

    def get_accounts(self) -> list[Account]:
        return [
            _acct("chq", AccountType.CHECKING, "4210.55"),
            _acct("sav", AccountType.SAVINGS, "15800.00"),
            _acct("tfsa", AccountType.TFSA, "11193.50", AccountCategory.INVESTMENT_ACCOUNT),
        ]

    def get_transactions(self, account_id: str) -> list[Transaction]:
        return []

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        return []


def _reader(store: ConsentStore, audit: AuditLog | None = None) -> ConsentEnforcingReader:
    return ConsentEnforcingReader(StubAdapter(), ConsentGate(store), audit)


def _delegate(store, scopes=REQUIRED_SCOPES, accounts=("chq", "sav", "tfsa")):
    return store.grant(
        CUSTOMER, AGENT_ID, scopes, duration=30 * DAY, account_ids=list(accounts), now=T0
    )


# --- Engine ------------------------------------------------------------------


def test_finds_idle_cash_and_estimates_gain() -> None:
    store = ConsentStore()
    _delegate(store)
    result = run_cash_finder(
        _reader(store),
        customer_id=CUSTOMER,
        account_ids=["chq", "sav", "tfsa"],
        source_label=lambda a: "Bank",
        at=T0 + DAY,
    )
    # Chequing: 4210.55 - 2000 buffer = 2210.55 idle; Savings: 15800 idle.
    assert result.idle_cash == Decimal("2210.55") + Decimal("15800.00")
    # TFSA (investment) is not a cash account — ignored, not "not counted".
    assert {a.account_id for a in result.analyzed} == {"chq", "sav"}
    assert result.not_counted == []
    assert result.target_rate == TARGET_RATE
    assert result.estimated_annual_gain > 0


def test_agent_bound_by_delegated_scope() -> None:
    # Delegation without BALANCES: the agent can see accounts but not their money.
    store = ConsentStore()
    _delegate(store, scopes=(ConsentScope.ACCOUNT_DETAILS,))
    result = run_cash_finder(
        _reader(store),
        customer_id=CUSTOMER,
        account_ids=["chq", "sav"],
        source_label=lambda a: None,
        at=T0 + DAY,
    )
    assert result.idle_cash == Decimal("0")
    assert {n.account_id for n in result.not_counted} == {"chq", "sav"}
    assert all("balance" in n.reason for n in result.not_counted)


def test_agent_access_is_logged_against_the_agent() -> None:
    store = ConsentStore()
    _delegate(store)
    audit = AuditLog()
    run_cash_finder(
        _reader(store, audit),
        customer_id=CUSTOMER,
        account_ids=["chq"],
        source_label=lambda a: None,
        at=T0 + DAY,
    )
    assert len(audit) > 0
    assert all(e.recipient == AGENT_ID for e in audit.all())  # attributed to the agent


# --- API + governance --------------------------------------------------------


def test_api_run_requires_active_delegation() -> None:
    client = TestClient(create_app())
    # Seeded delegation → run works.
    first = client.post("/api/agent/run")
    assert first.status_code == 200
    assert Decimal(first.json()["idleCash"]) > 0

    # Revoke it → the agent is powerless.
    assert client.post("/api/agent/delegation/revoke").status_code == 200
    assert client.get("/api/agent/delegation").json()["status"] == "REVOKED"
    assert client.post("/api/agent/run").status_code == 403

    # Re-delegate → it can act again.
    assert client.post("/api/agent/delegation").json()["status"] == "GRANTED"
    assert client.post("/api/agent/run").status_code == 200


def test_api_suggestion_is_advisory_and_traceable() -> None:
    client = TestClient(create_app())
    suggestion = client.post("/api/agent/run").json()
    assert "suggestion" in suggestion["advisory"].lower()
    assert suggestion["analyzed"]  # found some idle cash
    # The agent's reads show up in the traceability log, attributed to the agent.
    audit = client.get("/api/audit").json()
    assert any(e["recipient"] == AGENT_ID for e in audit)
