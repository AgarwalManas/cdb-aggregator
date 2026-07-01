"""Property-based tests for the security-critical invariants (item-24).

Example-based tests check the cases we thought of; these check the *invariant*
across thousands of randomized inputs — exactly where a subtle consent bug would
hide. Two properties, both load-bearing for the whole project:

1. **The gate allows a read iff an active, in-scope, account-covering grant
   exists.** No active grant, no data — never the other way around.
2. **Minimization never leaks an ungranted field.** A contact detail or a balance
   appears in the output only if its scope was granted.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.consent import (
    ConsentDenied,
    ConsentGate,
    ConsentStore,
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
    PersonName,
    PostalAddress,
)

SCOPES = list(ConsentScope)
ACCOUNTS = ["acc-1", "acc-2", "acc-3"]
BASE = datetime(2026, 1, 1, tzinfo=UTC)
CUSTOMER_ID = "cust"
RECIPIENT = "recipient"


# --- The consent gate --------------------------------------------------------

grant_strategy = st.fixed_dictionaries(
    {
        "scopes": st.sets(st.sampled_from(SCOPES), min_size=1),  # a consent grants >=1 scope
        "start_offset_days": st.integers(min_value=-30, max_value=30),
        "duration_days": st.integers(min_value=1, max_value=60),
        "account_ids": st.lists(st.sampled_from(ACCOUNTS), max_size=3, unique=True),
        "revoked": st.booleans(),
    }
)


@settings(max_examples=500)
@given(
    grants=st.lists(grant_strategy, max_size=5),
    query_scope=st.sampled_from(SCOPES),
    query_account=st.one_of(st.none(), st.sampled_from(ACCOUNTS)),
    query_offset_days=st.integers(min_value=-40, max_value=100),
)
def test_gate_allows_iff_a_qualifying_grant_exists(
    grants, query_scope, query_account, query_offset_days
):
    store = ConsentStore()
    built = []
    for i, spec in enumerate(grants):
        created = BASE + timedelta(days=spec["start_offset_days"])
        consent = store.grant(
            CUSTOMER_ID,
            RECIPIENT,
            spec["scopes"],
            duration=timedelta(days=spec["duration_days"]),
            account_ids=spec["account_ids"],
            now=created,
            consent_id=f"c-{i}",
        )
        if spec["revoked"]:
            consent = store.add(consent.revoke(at=created + timedelta(hours=1)))
        built.append(consent)

    at = BASE + timedelta(days=query_offset_days)
    gate = ConsentGate(store)
    decision = gate.check(CUSTOMER_ID, RECIPIENT, query_scope, account_id=query_account, at=at)

    # Independently recompute the invariant the gate is supposed to enforce.
    qualifying = [
        c
        for c in built
        if c.is_active(at)
        and query_scope in c.scopes
        and (query_account is None or c.covers_account(query_account))
    ]

    assert decision.allowed is bool(qualifying)
    if decision.allowed:
        assert decision.consent in qualifying
        assert decision.reason is None
        granted = gate.authorize(
            CUSTOMER_ID, RECIPIENT, query_scope, account_id=query_account, at=at
        )
        assert granted in qualifying
    else:
        assert decision.consent is None
        assert decision.reason is not None
        with pytest.raises(ConsentDenied):
            gate.authorize(CUSTOMER_ID, RECIPIENT, query_scope, account_id=query_account, at=at)


# --- Data minimization -------------------------------------------------------


def _customer_with_contact() -> Customer:
    return Customer(
        customer_id="c",
        name=PersonName(first="Ada", last="Lovelace"),
        emails=["ada@example.com"],
        phones=["+1-416-555-0100"],
        addresses=[
            PostalAddress(
                line1="1 Analytical Way", city="Toronto", postal_code="M5V 1A1", country="CA"
            )
        ],
    )


def _account_with_balance() -> Account:
    return Account(
        account_id="acc-1",
        customer_id="c",
        category=AccountCategory.DEPOSIT_ACCOUNT,
        account_type=AccountType.CHECKING,
        currency="CAD",
        balances=[Balance(as_of=BASE, currency="CAD", current="100.00")],
    )


@settings(max_examples=300)
@given(scopes=st.sets(st.sampled_from(SCOPES)))
def test_minimize_customer_never_leaks_contact(scopes):
    customer = _customer_with_contact()
    redacted, withheld = minimize_customer(customer, scopes)

    granted = ConsentScope.CUSTOMER_CONTACT in scopes
    leaked = bool(redacted.emails or redacted.phones or redacted.addresses)
    assert leaked <= granted  # a contact field appears only if the scope was granted
    assert withheld == (() if granted else ("contact",))
    # The original object is never mutated in place.
    assert customer.emails and customer.phones and customer.addresses


@settings(max_examples=300)
@given(scopes=st.sets(st.sampled_from(SCOPES)))
def test_minimize_account_never_leaks_balances(scopes):
    account = _account_with_balance()
    redacted, withheld = minimize_account(account, scopes)

    granted = ConsentScope.BALANCES in scopes
    leaked = bool(redacted.balances)
    assert leaked <= granted  # a balance appears only if the scope was granted
    assert withheld == (() if granted else ("balances",))
    assert account.balances  # original intact
