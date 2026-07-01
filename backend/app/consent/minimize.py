"""Data minimization — return only the fields a granted scope permits.

Maps to FDX's **Control** principle: consent is granular, so disclosure should be
too. Being *allowed* to read the customer record doesn't mean every field comes
back — contact details are withheld unless ``CUSTOMER_CONTACT`` was granted, and
balance amounts are withheld from an account unless ``BALANCES`` was granted.

Each function returns a redacted **copy** (the canonical objects are never
mutated in place) plus the names of the field clusters it withheld, so the audit
log (Item 8) can record what was minimized away as well as what was disclosed.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.models import Account, ConsentScope, Customer


def minimize_customer(
    customer: Customer, scopes: Iterable[ConsentScope]
) -> tuple[Customer, tuple[str, ...]]:
    """Withhold contact details unless ``CUSTOMER_CONTACT`` is granted.

    Identity (id + name + DOB) is assumed already gated on ``CUSTOMER_IDENTITY``
    by the caller; this strips the *contact* cluster when it wasn't granted.
    """
    if ConsentScope.CUSTOMER_CONTACT in set(scopes):
        return customer, ()
    redacted = customer.model_copy(update={"emails": [], "phones": [], "addresses": []})
    return redacted, ("contact",)


def minimize_account(
    account: Account, scopes: Iterable[ConsentScope]
) -> tuple[Account, tuple[str, ...]]:
    """Withhold balance amounts unless ``BALANCES`` is granted.

    An ``ACCOUNT_DETAILS`` grant reveals that an account exists and its metadata;
    the money on it requires the ``BALANCES`` scope.
    """
    if ConsentScope.BALANCES in set(scopes):
        return account, ()
    redacted = account.model_copy(update={"balances": []})
    return redacted, ("balances",)
