"""Canonical, FDX-aligned domain model.

Built in **Item 2**: Account, Balance, Transaction, InvestmentHolding, Customer,
and Consent — modeled on the FDX data model. This is the schema every data source
is normalized into (Items 3-5), and the schema the consent layer (Items 7-8)
gates access to.

Import canonical types straight from this package, e.g.::

    from app.models import Account, Consent, ConsentScope

The conventions shared by every type (Decimal money, ISO currency codes,
timezone-aware timestamps, camelCase/FDX serialization) live in
:mod:`app.models.common`.
"""

from __future__ import annotations

from .account import (
    CATEGORY_TYPES,
    Account,
    AccountCategory,
    AccountStatus,
    AccountType,
)
from .balance import Balance, BalanceType
from .common import (
    CountryCode,
    CurrencyCode,
    EmailStr,
    EntityId,
    FdxBaseModel,
    Money,
)
from .consent import Consent, ConsentScope, ConsentStatus
from .customer import Customer, PersonName, PostalAddress
from .holding import HoldingType, InvestmentHolding
from .transaction import DebitCreditMemo, Transaction, TransactionStatus

__all__ = [
    # Base / shared
    "FdxBaseModel",
    "CurrencyCode",
    "CountryCode",
    "EmailStr",
    "EntityId",
    "Money",
    # Account
    "Account",
    "AccountCategory",
    "AccountType",
    "AccountStatus",
    "CATEGORY_TYPES",
    # Balance
    "Balance",
    "BalanceType",
    # Transaction
    "Transaction",
    "TransactionStatus",
    "DebitCreditMemo",
    # Investment holding
    "InvestmentHolding",
    "HoldingType",
    # Customer
    "Customer",
    "PersonName",
    "PostalAddress",
    # Consent
    "Consent",
    "ConsentScope",
    "ConsentStatus",
]
