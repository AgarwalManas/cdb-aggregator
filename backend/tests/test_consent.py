"""Tests for the consent layer (Item 7): store lifecycle, gate, enforcement.

The enforcement path is the point of the whole project, so it gets the most
attention: every read must clear an active, in-scope, account-covering grant, and
each way that can fail has a distinct, asserted reason.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.base import SourceAdapter
from app.consent import (
    ConsentDenied,
    ConsentEnforcingReader,
    ConsentGate,
    ConsentStore,
    DenialReason,
)
from app.models import (
    Account,
    AccountCategory,
    AccountType,
    Balance,
    ConsentScope,
    ConsentStatus,
    Customer,
    DebitCreditMemo,
    InvestmentHolding,
    PersonName,
    Transaction,
    TransactionStatus,
)

CUSTOMER = "cust-1"
RECIPIENT = "aggregator"
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
DAY = timedelta(days=1)
ALL_SCOPES = set(ConsentScope)


# --- A stub source so enforcement is tested without providers ----------------

_ACC_CHQ = Account(
    account_id="acc-1",
    customer_id=CUSTOMER,
    category=AccountCategory.DEPOSIT_ACCOUNT,
    account_type=AccountType.CHECKING,
    currency="CAD",
    balances=[Balance(as_of=T0, currency="CAD", current="100.00")],
)
_ACC_INV = Account(
    account_id="acc-2",
    customer_id=CUSTOMER,
    category=AccountCategory.INVESTMENT_ACCOUNT,
    account_type=AccountType.TFSA,
    currency="CAD",
    balances=[Balance(as_of=T0, currency="CAD", current="5000.00")],
)
_TXN = Transaction(
    transaction_id="t-1",
    account_id="acc-1",
    amount="10.00",
    currency="CAD",
    debit_credit_memo=DebitCreditMemo.DEBIT,
    status=TransactionStatus.POSTED,
    transaction_timestamp=T0,
    posted_timestamp=T0,
)
_HOLDING = InvestmentHolding(
    holding_id="h-1",
    account_id="acc-2",
    holding_type="ETF",
    symbol="VFV",
    quantity="10",
    market_value="1000.00",
    currency="CAD",
    as_of=T0,
)


class StubAdapter(SourceAdapter):
    source_name = "stub"

    def get_customer(self) -> Customer:
        return Customer(customer_id=CUSTOMER, name=PersonName(first="Ada", last="Lovelace"))

    def get_accounts(self) -> list[Account]:
        return [_ACC_CHQ, _ACC_INV]

    def get_transactions(self, account_id: str) -> list[Transaction]:
        return [_TXN] if account_id == "acc-1" else []

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        return [_HOLDING] if account_id == "acc-2" else []


def _store_with_grant(scopes=ALL_SCOPES, *, account_ids=None) -> ConsentStore:
    store = ConsentStore()
    store.grant(CUSTOMER, RECIPIENT, scopes, duration=90 * DAY, account_ids=account_ids, now=T0)
    return store


def _reader(store: ConsentStore) -> ConsentEnforcingReader:
    return ConsentEnforcingReader(StubAdapter(), ConsentGate(store))


# --- Store lifecycle ---------------------------------------------------------


def test_grant_creates_active_consent() -> None:
    store = ConsentStore()
    consent = store.grant(CUSTOMER, RECIPIENT, {ConsentScope.BALANCES}, duration=30 * DAY, now=T0)
    assert consent.status is ConsentStatus.GRANTED
    assert consent.is_active(T0 + DAY)
    assert store.get(consent.consent_id) is consent
    assert store.for_customer(CUSTOMER) == [consent]


def test_revoke_replaces_with_inactive_grant() -> None:
    store = ConsentStore()
    consent = store.grant(CUSTOMER, RECIPIENT, {ConsentScope.BALANCES}, duration=30 * DAY, now=T0)
    revoked = store.revoke(consent.consent_id, now=T0 + DAY)
    assert revoked.status is ConsentStatus.REVOKED
    assert store.get(consent.consent_id).status is ConsentStatus.REVOKED  # replaced in place
    assert not revoked.is_active(T0 + 2 * DAY)


# --- Gate: allow + each denial reason ----------------------------------------


def test_gate_allows_active_in_scope_covered() -> None:
    gate = ConsentGate(_store_with_grant())
    decision = gate.check(
        CUSTOMER, RECIPIENT, ConsentScope.TRANSACTIONS, account_id="acc-1", at=T0 + DAY
    )
    assert decision.allowed
    assert decision.consent is not None


def test_gate_denies_when_no_consent() -> None:
    gate = ConsentGate(ConsentStore())
    decision = gate.check(CUSTOMER, RECIPIENT, ConsentScope.ACCOUNT_DETAILS, at=T0 + DAY)
    assert not decision.allowed
    assert decision.reason is DenialReason.NO_CONSENT


def test_gate_denies_when_expired() -> None:
    gate = ConsentGate(_store_with_grant())
    decision = gate.check(CUSTOMER, RECIPIENT, ConsentScope.ACCOUNT_DETAILS, at=T0 + 200 * DAY)
    assert decision.reason is DenialReason.INACTIVE


def test_gate_denies_when_revoked() -> None:
    store = _store_with_grant()
    store.revoke(store.all()[0].consent_id, now=T0 + DAY)
    gate = ConsentGate(store)
    decision = gate.check(CUSTOMER, RECIPIENT, ConsentScope.ACCOUNT_DETAILS, at=T0 + 2 * DAY)
    assert decision.reason is DenialReason.INACTIVE


def test_gate_denies_scope_not_granted() -> None:
    gate = ConsentGate(_store_with_grant({ConsentScope.BALANCES}))
    decision = gate.check(
        CUSTOMER, RECIPIENT, ConsentScope.TRANSACTIONS, account_id="acc-1", at=T0 + DAY
    )
    assert decision.reason is DenialReason.SCOPE_NOT_GRANTED


def test_gate_denies_account_not_covered() -> None:
    gate = ConsentGate(_store_with_grant(account_ids=["acc-1"]))
    covered = gate.check(
        CUSTOMER, RECIPIENT, ConsentScope.TRANSACTIONS, account_id="acc-1", at=T0 + DAY
    )
    uncovered = gate.check(
        CUSTOMER, RECIPIENT, ConsentScope.TRANSACTIONS, account_id="acc-2", at=T0 + DAY
    )
    assert covered.allowed
    assert uncovered.reason is DenialReason.ACCOUNT_NOT_COVERED


def test_authorize_raises_with_decision() -> None:
    gate = ConsentGate(ConsentStore())
    with pytest.raises(ConsentDenied) as exc:
        gate.authorize(CUSTOMER, RECIPIENT, ConsentScope.ACCOUNT_DETAILS, at=T0 + DAY)
    assert exc.value.decision.reason is DenialReason.NO_CONSENT


# --- Reader: enforcement in front of real reads ------------------------------


def test_reader_allows_all_reads_with_full_grant() -> None:
    reader = _reader(_store_with_grant())
    at = T0 + DAY
    assert reader.read_customer(CUSTOMER, RECIPIENT, at=at).customer_id == CUSTOMER
    assert {a.account_id for a in reader.read_accounts(CUSTOMER, RECIPIENT, at=at)} == {
        "acc-1",
        "acc-2",
    }
    assert reader.read_balances(CUSTOMER, RECIPIENT, "acc-1", at=at)[0].current is not None
    assert reader.read_transactions(CUSTOMER, RECIPIENT, "acc-1", at=at)[0].transaction_id == "t-1"
    assert reader.read_holdings(CUSTOMER, RECIPIENT, "acc-2", at=at)[0].symbol == "VFV"


def test_reader_denies_without_any_consent() -> None:
    reader = _reader(ConsentStore())
    with pytest.raises(ConsentDenied) as exc:
        reader.read_accounts(CUSTOMER, RECIPIENT, at=T0 + DAY)
    assert exc.value.decision.reason is DenialReason.NO_CONSENT


def test_reader_enforces_per_scope() -> None:
    # Everything except TRANSACTIONS.
    reader = _reader(_store_with_grant(ALL_SCOPES - {ConsentScope.TRANSACTIONS}))
    at = T0 + DAY
    reader.read_accounts(CUSTOMER, RECIPIENT, at=at)  # ACCOUNT_DETAILS: fine
    with pytest.raises(ConsentDenied) as exc:
        reader.read_transactions(CUSTOMER, RECIPIENT, "acc-1", at=at)
    assert exc.value.decision.reason is DenialReason.SCOPE_NOT_GRANTED


def test_reader_denies_after_expiry_and_revocation() -> None:
    store = _store_with_grant()
    reader = _reader(store)
    # Expired (read far in the future).
    with pytest.raises(ConsentDenied) as expired:
        reader.read_accounts(CUSTOMER, RECIPIENT, at=T0 + 200 * DAY)
    assert expired.value.decision.reason is DenialReason.INACTIVE
    # Revoked (one-tap revoke, then read within the window).
    store.revoke(store.all()[0].consent_id, now=T0 + DAY)
    with pytest.raises(ConsentDenied) as revoked:
        reader.read_accounts(CUSTOMER, RECIPIENT, at=T0 + 2 * DAY)
    assert revoked.value.decision.reason is DenialReason.INACTIVE


def test_reader_enforces_account_coverage() -> None:
    reader = _reader(_store_with_grant(account_ids=["acc-1"]))
    at = T0 + DAY
    reader.read_transactions(CUSTOMER, RECIPIENT, "acc-1", at=at)  # covered
    with pytest.raises(ConsentDenied) as exc:
        reader.read_holdings(CUSTOMER, RECIPIENT, "acc-2", at=at)  # not covered
    assert exc.value.decision.reason is DenialReason.ACCOUNT_NOT_COVERED
