"""Tests for traceability + data minimization (Item 8).

Two FDX principles, exercised through the enforcing reader:

* **Control** — a read returns only the fields the granted scopes permit
  (contact withheld without ``CUSTOMER_CONTACT``; balances without ``BALANCES``).
* **Traceability** — every access, allowed or denied, lands in the append-only
  audit log, tied to the grant it relied on and noting what was minimized away.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.base import SourceAdapter
from app.consent import (
    GENESIS_HASH,
    AuditEvent,
    AuditLog,
    ConsentDenied,
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
    PostalAddress,
    Transaction,
)

CUSTOMER = "cust-1"
RECIPIENT = "aggregator"
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
DAY = timedelta(days=1)
ALL_SCOPES = set(ConsentScope)

_CUSTOMER = Customer(
    customer_id=CUSTOMER,
    name=PersonName(first="Ada", last="Lovelace"),
    emails=["ada@example.com"],
    addresses=[
        PostalAddress(line1="1 Analytical Way", city="Toronto", postal_code="M5V 1A1", country="CA")
    ],
)
_ACCOUNT = Account(
    account_id="acc-1",
    customer_id=CUSTOMER,
    category=AccountCategory.DEPOSIT_ACCOUNT,
    account_type=AccountType.CHECKING,
    currency="CAD",
    balances=[Balance(as_of=T0, currency="CAD", current="100.00")],
)


class StubAdapter(SourceAdapter):
    source_name = "stub"

    def get_customer(self) -> Customer:
        return _CUSTOMER

    def get_accounts(self) -> list[Account]:
        return [_ACCOUNT]

    def get_transactions(self, account_id: str) -> list[Transaction]:
        return []

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        return []


def _reader(scopes, *, audit: AuditLog | None = None) -> ConsentEnforcingReader:
    store = ConsentStore()
    store.grant(CUSTOMER, RECIPIENT, scopes, duration=90 * DAY, now=T0)
    return ConsentEnforcingReader(StubAdapter(), ConsentGate(store), audit=audit)


# --- Minimization (unit) -----------------------------------------------------


def test_minimize_customer_withholds_contact_without_scope() -> None:
    redacted, withheld = minimize_customer(_CUSTOMER, {ConsentScope.CUSTOMER_IDENTITY})
    assert redacted.name.full == "Ada Lovelace"  # identity kept
    assert redacted.emails == [] and redacted.addresses == []  # contact stripped
    assert withheld == ("contact",)


def test_minimize_customer_keeps_contact_with_scope() -> None:
    kept, withheld = minimize_customer(
        _CUSTOMER, {ConsentScope.CUSTOMER_IDENTITY, ConsentScope.CUSTOMER_CONTACT}
    )
    assert kept.emails == ["ada@example.com"]
    assert withheld == ()


def test_minimize_account_withholds_balances_without_scope() -> None:
    redacted, withheld = minimize_account(_ACCOUNT, {ConsentScope.ACCOUNT_DETAILS})
    assert redacted.account_id == "acc-1"  # metadata kept
    assert redacted.balances == []  # amounts withheld
    assert withheld == ("balances",)
    # The original is untouched (redaction returns a copy).
    assert _ACCOUNT.balances[0].current is not None


def test_minimize_account_keeps_balances_with_scope() -> None:
    kept, withheld = minimize_account(
        _ACCOUNT, {ConsentScope.ACCOUNT_DETAILS, ConsentScope.BALANCES}
    )
    assert kept.balances[0].current is not None
    assert withheld == ()


# --- Minimization through the reader -----------------------------------------


def test_reader_minimizes_customer_contact() -> None:
    reader = _reader({ConsentScope.CUSTOMER_IDENTITY})  # no CONTACT
    customer = reader.read_customer(CUSTOMER, RECIPIENT, at=T0 + DAY)
    assert customer.name.full == "Ada Lovelace"
    assert customer.emails == []  # withheld


def test_reader_minimizes_account_balances() -> None:
    reader = _reader({ConsentScope.ACCOUNT_DETAILS})  # no BALANCES
    (account,) = reader.read_accounts(CUSTOMER, RECIPIENT, at=T0 + DAY)
    assert account.balances == []  # withheld
    # With BALANCES too, the amounts come through.
    reader2 = _reader({ConsentScope.ACCOUNT_DETAILS, ConsentScope.BALANCES})
    (account2,) = reader2.read_accounts(CUSTOMER, RECIPIENT, at=T0 + DAY)
    assert account2.balances[0].current is not None


# --- Traceability audit log --------------------------------------------------


def test_every_read_is_logged_with_grant() -> None:
    audit = AuditLog()
    reader = _reader(ALL_SCOPES, audit=audit)
    reader.read_accounts(CUSTOMER, RECIPIENT, at=T0 + DAY)
    reader.read_transactions(CUSTOMER, RECIPIENT, "acc-1", at=T0 + DAY)

    events = audit.all()
    assert [e.action for e in events] == ["read_accounts", "read_transactions"]
    assert all(e.allowed for e in events)
    assert all(e.consent_id is not None for e in events)  # tied to the grant
    assert audit.for_customer(CUSTOMER) == events


def test_denied_access_is_logged() -> None:
    audit = AuditLog()
    reader = ConsentEnforcingReader(StubAdapter(), ConsentGate(ConsentStore()), audit=audit)
    with pytest.raises(ConsentDenied):
        reader.read_accounts(CUSTOMER, RECIPIENT, at=T0 + DAY)

    (event,) = audit.all()
    assert event.allowed is False
    assert event.reason is DenialReason.NO_CONSENT
    assert event.consent_id is None
    assert event.record_count == 0


def test_audit_records_what_was_minimized() -> None:
    audit = AuditLog()
    reader = _reader({ConsentScope.ACCOUNT_DETAILS}, audit=audit)  # no BALANCES
    reader.read_accounts(CUSTOMER, RECIPIENT, at=T0 + DAY)

    (event,) = audit.all()
    assert event.allowed is True
    assert event.record_count == 1
    assert event.withheld == ("balances",)  # the trail notes the redaction


def test_audit_is_append_only_and_queryable_by_consent() -> None:
    audit = AuditLog()
    store = ConsentStore()
    consent = store.grant(CUSTOMER, RECIPIENT, ALL_SCOPES, duration=90 * DAY, now=T0)
    reader = ConsentEnforcingReader(StubAdapter(), ConsentGate(store), audit=audit)

    reader.read_customer(CUSTOMER, RECIPIENT, at=T0 + DAY)
    reader.read_accounts(CUSTOMER, RECIPIENT, at=T0 + DAY)
    assert len(audit) == 2
    # Every event ties back to the one grant.
    assert audit.for_consent(consent.consent_id) == audit.all()
    # No API to remove or mutate — append is the only mutation.
    assert not hasattr(audit, "delete")
    assert not hasattr(audit, "clear")


# --- Tamper-evident hash chain (item-22) -------------------------------------


def _event(i: int) -> AuditEvent:
    return AuditEvent(
        occurred_at=T0 + i * DAY,
        action=f"read_{i}",
        customer_id=CUSTOMER,
        recipient=RECIPIENT,
        scope=ConsentScope.BALANCES,
        allowed=True,
        record_count=1,
    )


def _chained_log(n: int = 4) -> AuditLog:
    log = AuditLog()
    for i in range(n):
        log.record(_event(i))
    return log


def test_head_is_genesis_when_empty() -> None:
    assert AuditLog().head() == GENESIS_HASH


def test_each_entry_links_to_the_previous_hash() -> None:
    log = _chained_log(3)
    entries = log.chain()
    assert entries[0].prev_hash == GENESIS_HASH
    assert entries[1].prev_hash == entries[0].entry_hash
    assert entries[2].prev_hash == entries[1].entry_hash
    assert log.head() == entries[-1].entry_hash


def test_verify_passes_for_an_intact_chain() -> None:
    result = _chained_log(4).verify()
    assert result.valid is True
    assert result.checked == 4
    assert result.broken_at is None


def test_verify_detects_an_edited_entry() -> None:
    log = _chained_log(4)
    # Simulate editing a stored record's content without re-hashing it.
    edited = replace(log._entries[2].event, record_count=999)
    log._entries[2] = replace(log._entries[2], event=edited)

    result = log.verify()
    assert result.valid is False
    assert result.broken_at == 2  # the altered entry no longer matches its hash


def test_verify_detects_a_deleted_entry() -> None:
    log = _chained_log(4)
    del log._entries[1]  # removing a middle entry breaks the linkage after the gap

    result = log.verify()
    assert result.valid is False
    assert result.broken_at == 1  # the next entry's prev_hash no longer lines up
