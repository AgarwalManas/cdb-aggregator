"""Hardening tests (Item 12): edge cases and error paths.

Broadens coverage across the parts most worth trusting — the adapters' parsing
and error wrapping, consent enforcement inside aggregation, data minimization
corner cases, and the agent's governance branches. These are the paths a happy-
path demo never hits but a real integration would.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.adapters.base import (
    NormalizationError,
    SourceAdapter,
    normalize,
    parse_iso8601,
    to_decimal,
)
from app.adapters.fdx_bank import FdxHttpClient
from app.adapters.legacy_bank import LegacyHttpClient, _parse_address
from app.adapters.scraper_bank import (
    HtmlStatementClient,
    parse_accounts,
    parse_customer,
    parse_statement_date,
    parse_transactions,
)
from app.agent import AGENT_ID, run_cash_finder
from app.api.aggregation import merged_accounts, merged_transactions
from app.api.demo import AggregatorState, Connection
from app.consent import (
    AuditLog,
    ConsentEnforcingReader,
    ConsentGate,
    ConsentStore,
    DenialReason,
    minimize_account,
    minimize_customer,
)
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
from app.providers.legacy_bank.auth import LEGACY_PASS, LEGACY_USER
from app.providers.mock_fdx_bank.app import create_app as create_fdx_app
from app.providers.mock_fdx_bank.auth import CLIENT_ID, CLIENT_SECRET
from app.providers.scraper_bank import data as scraper_data
from app.providers.scraper_bank.app import create_app as create_scraper_app
from app.providers.scraper_bank.auth import OLDBANK_PASS, OLDBANK_USER

T0 = datetime(2026, 1, 1, tzinfo=UTC)
DAY = timedelta(days=1)


# --- Shared stub source ------------------------------------------------------


def _acct(account_id, atype, current, category=AccountCategory.DEPOSIT_ACCOUNT) -> Account:
    return Account(
        account_id=account_id,
        customer_id="c",
        category=category,
        account_type=atype,
        currency="CAD",
        balances=[Balance(as_of=T0, currency="CAD", current=current)],
    )


class StubAdapter(SourceAdapter):
    source_name = "stub"

    def get_customer(self) -> Customer:
        return Customer(customer_id="c", name=PersonName(first="Ada", last="Lovelace"))

    def get_accounts(self) -> list[Account]:
        return [
            _acct("acc-1", AccountType.CHECKING, "4210.55"),
            _acct("small", AccountType.CHECKING, "1500.00"),
        ]

    def get_transactions(self, account_id: str) -> list[Transaction]:
        return []

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        return []


# --- Adapter base helpers ----------------------------------------------------


def test_to_decimal_variants() -> None:
    assert to_decimal(Decimal("5.00")) == Decimal("5.00")  # passthrough
    assert to_decimal("$1,234.50") == Decimal("1234.50")  # strips $ and comma
    assert to_decimal(42) == Decimal("42")
    with pytest.raises(ValueError, match="not a decimal"):
        to_decimal("not-a-number")


def test_parse_iso8601_accepts_z() -> None:
    assert parse_iso8601("2026-06-27T14:30:00Z").tzinfo is not None


def test_normalize_wraps_and_passes_through() -> None:
    # A plain error is wrapped with context.
    with pytest.raises(NormalizationError) as wrapped:
        normalize("src", "thing", "id-1", lambda _: (_ for _ in ()).throw(ValueError("boom")), {})
    assert wrapped.value.source == "src" and wrapped.value.identifier == "id-1"

    # An existing NormalizationError is not double-wrapped.
    inner = NormalizationError("s", "e", "i", ValueError("x"))

    def raise_inner(_):
        raise inner

    with pytest.raises(NormalizationError) as passed:
        normalize("other", "e", "i", raise_inner, {})
    assert passed.value is inner


# --- Legacy address parsing branches -----------------------------------------


def test_parse_address_fallbacks() -> None:
    assert _parse_address(None) is None
    assert _parse_address("just one line") is None  # too few comma segments
    assert _parse_address("line1, tooShortMiddle, CA") is None  # middle < 3 tokens
    good = _parse_address("1 Analytical Way, Toronto ON M5V 1A1, CA")
    assert good is not None and good.city == "Toronto" and good.postal_code == "M5V 1A1"


# --- Scraper parsing branches ------------------------------------------------


def test_scraper_parse_error_paths() -> None:
    html = scraper_data.render_statement_html()
    # An account with no transactions table yields an empty list, not an error.
    assert parse_transactions(html, "****5678") == []
    # Unknown account block.
    with pytest.raises(ValueError, match="no account block"):
        parse_transactions(html, "****0000")
    # Missing structure.
    with pytest.raises(ValueError, match="account holder not found"):
        parse_customer("<html><body></body></html>")
    with pytest.raises(ValueError, match="statement date not found"):
        parse_statement_date("<html><body></body></html>")
    with pytest.raises(ValueError, match="no accounts found"):
        parse_accounts('<html><body><p class="statement-date">As of: 2026-06-30</p></body></html>')


# --- Transport client edge cases ---------------------------------------------


def test_http_clients_unknown_account_and_close() -> None:
    legacy = LegacyHttpClient(TestClient(create_legacy_app()), LEGACY_USER, LEGACY_PASS)
    with pytest.raises(KeyError):
        legacy.get_account("nope")
    legacy.close()

    scraper = HtmlStatementClient(TestClient(create_scraper_app()), OLDBANK_USER, OLDBANK_PASS)
    with pytest.raises(KeyError):
        scraper.get_account("nope")
    scraper.close()

    fdx = FdxHttpClient(TestClient(create_fdx_app()), CLIENT_ID, CLIENT_SECRET)
    assert fdx.get_holdings("acc-chq-001") == []  # a non-investment account has none
    fdx.close()


# --- Consent enforcement corner cases ----------------------------------------


def test_future_dated_grant_is_not_yet_active() -> None:
    store = ConsentStore()
    store.grant("c", "r", {ConsentScope.ACCOUNT_DETAILS}, duration=30 * DAY, now=T0 + 10 * DAY)
    gate = ConsentGate(store)
    # Checked "now" (before it starts) -> inactive.
    decision = gate.check("c", "r", ConsentScope.ACCOUNT_DETAILS, at=T0)
    assert decision.reason is DenialReason.INACTIVE


def test_scopes_and_accounts_union_across_grants() -> None:
    store = ConsentStore()
    store.grant("c", "r", {ConsentScope.BALANCES}, duration=30 * DAY, account_ids=["a1"], now=T0)
    store.grant(
        "c", "r", {ConsentScope.TRANSACTIONS}, duration=30 * DAY, account_ids=["a2"], now=T0
    )
    gate = ConsentGate(store)
    at = T0 + DAY
    assert gate.check("c", "r", ConsentScope.BALANCES, account_id="a1", at=at).allowed
    assert gate.check("c", "r", ConsentScope.TRANSACTIONS, account_id="a2", at=at).allowed
    # But a scope only one grant has doesn't apply to the other's account.
    assert not gate.check("c", "r", ConsentScope.BALANCES, account_id="a2", at=at).allowed


def test_reader_missing_account_raises_keyerror() -> None:
    store = ConsentStore()
    store.grant("c", "r", {ConsentScope.BALANCES}, duration=30 * DAY, account_ids=["ghost"], now=T0)
    reader = ConsentEnforcingReader(StubAdapter(), ConsentGate(store))
    # Gate allows (ghost is covered), but the adapter has no such account.
    with pytest.raises(KeyError):
        reader.read_balances("c", "r", "ghost", at=T0 + DAY)


# --- Aggregation skips denied reads ------------------------------------------


def _state_with(consent_scopes, account_ids) -> AggregatorState:
    store = ConsentStore()
    store.grant(
        "c",
        "cdb-aggregator",
        consent_scopes,
        duration=30 * DAY,
        account_ids=account_ids,
        now=T0,
        consent_id="con-x",
    )
    return AggregatorState(
        store=store,
        audit=AuditLog(),
        connections=[Connection("con-x", "mock_fdx_bank", "Mock FDX Bank")],
        adapter=StubAdapter(),
        customer_id="c",
        recipient="cdb-aggregator",
    )


def test_aggregation_skips_reads_it_cannot_make() -> None:
    # Connection is active but grants neither ACCOUNT_DETAILS nor TRANSACTIONS.
    state = _state_with({ConsentScope.BALANCES}, ["acc-1"])
    assert merged_accounts(state, at=T0 + DAY) == []  # read_account denied -> skipped
    assert merged_transactions(state, at=T0 + DAY) == []  # read_transactions denied -> skipped


# --- Data minimization corner cases ------------------------------------------


def test_minimize_account_with_no_balances() -> None:
    account = Account(
        account_id="a",
        category=AccountCategory.DEPOSIT_ACCOUNT,
        account_type=AccountType.CHECKING,
        currency="CAD",
        balances=[],
    )
    kept, withheld = minimize_account(account, {ConsentScope.BALANCES})
    assert kept.balances == [] and withheld == ()
    stripped, withheld2 = minimize_account(account, set())
    assert stripped.balances == [] and withheld2 == ("balances",)


def test_minimize_customer_no_scopes_strips_contact() -> None:
    customer = Customer(
        customer_id="c",
        name=PersonName(first="Ada", last="Lovelace"),
        emails=["ada@example.com"],
    )
    stripped, withheld = minimize_customer(customer, set())
    assert stripped.emails == [] and withheld == ("contact",)


# --- Agent governance branches -----------------------------------------------


def test_agent_skips_below_buffer_and_uncovered() -> None:
    store = ConsentStore()
    store.grant(
        "c",
        AGENT_ID,
        {ConsentScope.ACCOUNT_DETAILS, ConsentScope.BALANCES},
        duration=30 * DAY,
        account_ids=["small"],
        now=T0,
    )
    reader = ConsentEnforcingReader(StubAdapter(), ConsentGate(store))

    # 'small' is below the chequing buffer -> no idle cash, not an error.
    result = run_cash_finder(
        reader, customer_id="c", account_ids=["small"], source_label=lambda a: None, at=T0 + DAY
    )
    assert result.idle_cash == Decimal("0")
    assert result.analyzed == [] and result.not_counted == []

    # An account outside the delegation -> denied -> reported as not counted.
    result2 = run_cash_finder(
        reader, customer_id="c", account_ids=["acc-1"], source_label=lambda a: None, at=T0 + DAY
    )
    assert {n.account_id for n in result2.not_counted} == {"acc-1"}
    assert "not permitted" in result2.not_counted[0].reason
