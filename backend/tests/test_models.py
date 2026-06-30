"""Unit tests for the canonical, FDX-aligned domain model (Item 2).

Coverage is organized by entity, with extra attention on the cross-field
validators and on ``Consent``'s behavior — those are the parts later items
(normalizer, consent enforcement, audit log) build directly on, so they're the
parts most worth pinning down now.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import (
    Account,
    AccountCategory,
    AccountStatus,
    AccountType,
    Balance,
    BalanceType,
    Consent,
    ConsentScope,
    ConsentStatus,
    Customer,
    DebitCreditMemo,
    InvestmentHolding,
    PersonName,
    PostalAddress,
    Transaction,
    TransactionStatus,
)

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


# --- common field types ------------------------------------------------------


def test_currency_must_be_iso_4217_format() -> None:
    Balance(as_of=T0, currency="CAD", current=Decimal("100"))  # ok
    for bad in ["cad", "CAImport", "CA", "12A", "C$D"]:
        with pytest.raises(ValidationError):
            Balance(as_of=T0, currency=bad, current=Decimal("100"))


def test_entity_id_rejects_empty_or_whitespace() -> None:
    with pytest.raises(ValidationError):
        Account(
            account_id="   ",  # stripped to empty
            category=AccountCategory.DEPOSIT_ACCOUNT,
            account_type=AccountType.CHECKING,
            currency="CAD",
        )


def test_naive_datetime_is_rejected() -> None:
    """Timestamps must be timezone-aware."""
    with pytest.raises(ValidationError):
        Balance(as_of=datetime(2026, 1, 1, 12, 0), currency="CAD", current=Decimal("1"))


def test_money_keeps_decimal_precision() -> None:
    bal = Balance(as_of=T0, currency="CAD", current="0.10")
    assert bal.current == Decimal("0.10")
    # JSON output is a string, not a lossy binary float — that's the point.
    serialized = bal.model_dump(by_alias=True, mode="json")["current"]
    assert isinstance(serialized, str)
    assert Decimal(serialized) == Decimal("0.10")


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        Balance(as_of=T0, currency="CAD", current=Decimal("1"), surprise="!")


# --- Balance -----------------------------------------------------------------


def test_balance_available_may_not_exceed_current_for_asset() -> None:
    with pytest.raises(ValidationError):
        Balance(
            as_of=T0,
            currency="CAD",
            current=Decimal("50"),
            available=Decimal("75"),
            balance_type=BalanceType.ASSET,
        )


def test_balance_liability_allows_available_above_current() -> None:
    # For a liability, "available" is available credit — a different quantity.
    bal = Balance(
        as_of=T0,
        currency="CAD",
        current=Decimal("-200"),
        available=Decimal("800"),
        balance_type=BalanceType.LIABILITY,
    )
    assert bal.available == Decimal("800")


# --- Account -----------------------------------------------------------------


def test_account_valid_with_nested_balance() -> None:
    acct = Account(
        account_id="acct-1",
        customer_id="cust-1",
        category=AccountCategory.INVESTMENT_ACCOUNT,
        account_type=AccountType.TFSA,
        currency="CAD",
        balances=[Balance(as_of=T0, currency="CAD", current=Decimal("1000"))],
    )
    assert acct.status is AccountStatus.OPEN  # default
    assert acct.balances[0].current == Decimal("1000")


def test_account_type_must_match_category() -> None:
    with pytest.raises(ValidationError, match="not valid for category"):
        Account(
            account_id="acct-1",
            category=AccountCategory.LOAN_ACCOUNT,
            account_type=AccountType.CHECKING,  # checking isn't a loan type
            currency="CAD",
        )


@pytest.mark.parametrize(
    ("category", "account_type"),
    [
        (AccountCategory.DEPOSIT_ACCOUNT, AccountType.CHECKING),
        (AccountCategory.LOAN_ACCOUNT, AccountType.MORTGAGE),
        (AccountCategory.INVESTMENT_ACCOUNT, AccountType.RRSP),
        (AccountCategory.INSURANCE_ACCOUNT, AccountType.ANNUITY),
    ],
)
def test_account_type_category_pairs_accepted(
    category: AccountCategory, account_type: AccountType
) -> None:
    acct = Account(account_id="a", category=category, account_type=account_type, currency="USD")
    assert acct.category is category and acct.account_type is account_type


# --- Transaction -------------------------------------------------------------


def _posted_txn(**overrides) -> Transaction:
    base = dict(
        transaction_id="txn-1",
        account_id="acct-1",
        amount=Decimal("12.34"),
        currency="CAD",
        debit_credit_memo=DebitCreditMemo.DEBIT,
        status=TransactionStatus.POSTED,
        transaction_timestamp=T0,
        posted_timestamp=T0,
    )
    base.update(overrides)
    return Transaction(**base)


def test_transaction_amount_must_be_positive() -> None:
    for bad in [Decimal("0"), Decimal("-5")]:
        with pytest.raises(ValidationError, match="must be positive"):
            _posted_txn(amount=bad)


def test_posted_transaction_requires_posted_timestamp() -> None:
    with pytest.raises(ValidationError, match="POSTED transaction requires"):
        _posted_txn(posted_timestamp=None)


def test_pending_transaction_must_not_have_posted_timestamp() -> None:
    with pytest.raises(ValidationError, match="PENDING transaction must not"):
        _posted_txn(status=TransactionStatus.PENDING, posted_timestamp=T0)
    # The valid pending shape: no posted_timestamp.
    txn = _posted_txn(status=TransactionStatus.PENDING, posted_timestamp=None)
    assert txn.status is TransactionStatus.PENDING


# --- InvestmentHolding -------------------------------------------------------


def test_holding_derives_market_value_from_quantity_and_price() -> None:
    h = InvestmentHolding(
        holding_id="h-1",
        account_id="acct-1",
        holding_type="ETF",
        symbol="VFV",
        quantity=Decimal("10"),
        current_unit_price=Decimal("100.25"),
        currency="CAD",
        as_of=T0,
    )
    assert h.market_value == Decimal("1002.5000")


def test_holding_requires_value_or_price() -> None:
    with pytest.raises(ValidationError, match="market_value is required"):
        InvestmentHolding(
            holding_id="h-1",
            account_id="acct-1",
            holding_type="CASH",
            quantity=Decimal("1"),
            currency="CAD",
            as_of=T0,
        )


def test_holding_quantity_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        InvestmentHolding(
            holding_id="h-1",
            account_id="acct-1",
            holding_type="EQUITY",
            quantity=Decimal("-1"),
            market_value=Decimal("10"),
            currency="CAD",
            as_of=T0,
        )


# --- Customer ----------------------------------------------------------------


def test_customer_full_name_and_contact() -> None:
    c = Customer(
        customer_id="cust-1",
        name=PersonName(first="Ada", last="Lovelace"),
        emails=["ada@example.com"],
        addresses=[
            PostalAddress(
                line1="1 Analytical Way",
                city="Toronto",
                region="ON",
                postal_code="M5V 1A1",
                country="CA",
            )
        ],
    )
    assert c.name.full == "Ada Lovelace"
    assert c.addresses[0].country == "CA"


def test_customer_rejects_bad_email_and_country() -> None:
    with pytest.raises(ValidationError):
        Customer(
            customer_id="c",
            name=PersonName(first="A", last="B"),
            emails=["not-an-email"],
        )
    with pytest.raises(ValidationError):
        PostalAddress(line1="x", city="y", postal_code="z", country="Canada")


def test_customer_dob_cannot_be_in_future() -> None:
    future = (datetime.now(UTC) + timedelta(days=365)).date()
    with pytest.raises(ValidationError, match="cannot be in the future"):
        Customer(
            customer_id="c",
            name=PersonName(first="A", last="B"),
            date_of_birth=future,
        )


# --- Consent (the star) ------------------------------------------------------


def _consent(**overrides) -> Consent:
    base = dict(
        consent_id="consent-1",
        customer_id="cust-1",
        recipient="cdb-aggregator",
        scopes={ConsentScope.BALANCES, ConsentScope.TRANSACTIONS},
        status=ConsentStatus.GRANTED,
        created_at=T0,
        expires_at=T0 + timedelta(days=90),
    )
    base.update(overrides)
    return Consent(**base)


def test_consent_requires_at_least_one_scope() -> None:
    with pytest.raises(ValidationError, match="at least one scope"):
        _consent(scopes=set())


def test_consent_expiry_must_be_after_creation() -> None:
    with pytest.raises(ValidationError, match="expires_at must be after"):
        _consent(expires_at=T0 - timedelta(days=1))


def test_consent_revocation_consistency() -> None:
    # REVOKED without a timestamp is invalid...
    with pytest.raises(ValidationError, match="requires a revoked_at"):
        _consent(status=ConsentStatus.REVOKED)
    # ...and a timestamp without REVOKED status is invalid too.
    with pytest.raises(ValidationError, match="status is not REVOKED"):
        _consent(revoked_at=T0 + timedelta(days=1))


def test_consent_is_active_within_window() -> None:
    c = _consent()
    assert c.is_active(T0 + timedelta(days=1)) is True


def test_consent_not_active_before_start_or_after_expiry() -> None:
    c = _consent()
    assert c.is_active(T0 - timedelta(seconds=1)) is False  # before start
    assert c.is_active(T0 + timedelta(days=90)) is False  # at/after expiry
    assert c.effective_status(T0 + timedelta(days=91)) is ConsentStatus.EXPIRED


def test_consent_pending_is_not_active() -> None:
    c = _consent(status=ConsentStatus.PENDING)
    assert c.is_active(T0 + timedelta(days=1)) is False


def test_consent_permits_only_granted_scopes_while_active() -> None:
    c = _consent()
    at = T0 + timedelta(days=1)
    assert c.permits(ConsentScope.BALANCES, at) is True
    assert c.permits(ConsentScope.INVESTMENT_HOLDINGS, at) is False  # not granted
    # An in-scope check still fails once expired.
    assert c.permits(ConsentScope.BALANCES, T0 + timedelta(days=200)) is False


def test_consent_revoke_returns_new_inactive_instance() -> None:
    c = _consent()
    at = T0 + timedelta(days=2)
    revoked = c.revoke(at)
    assert revoked is not c
    assert c.status is ConsentStatus.GRANTED  # original untouched
    assert revoked.status is ConsentStatus.REVOKED
    assert revoked.revoked_at == at
    assert revoked.is_active(T0 + timedelta(days=3)) is False
    assert revoked.effective_status() is ConsentStatus.REVOKED


def test_consent_account_scoping() -> None:
    full = _consent(account_ids=[])
    assert full.covers_account("any-account") is True  # empty == all
    scoped = _consent(account_ids=["acct-1", "acct-2"])
    assert scoped.covers_account("acct-1") is True
    assert scoped.covers_account("acct-9") is False


# --- FDX-shaped serialization ------------------------------------------------


def test_serializes_to_camelcase_and_round_trips() -> None:
    acct = Account(
        account_id="acct-1",
        customer_id="cust-1",
        category=AccountCategory.DEPOSIT_ACCOUNT,
        account_type=AccountType.CHECKING,
        currency="CAD",
        masked_number="****1234",
    )
    wire = acct.model_dump(by_alias=True, mode="json")
    # FDX wire format is camelCase.
    assert wire["accountId"] == "acct-1"
    assert wire["accountType"] == "CHECKING"
    assert wire["maskedNumber"] == "****1234"
    # And it parses back from that same camelCase payload.
    assert Account.model_validate(wire) == acct


def test_accepts_snake_case_input_too() -> None:
    """populate_by_name lets internal code construct with field names."""
    txn = _posted_txn()
    assert txn.debit_credit_memo is DebitCreditMemo.DEBIT
