"""Account — the central canonical entity.

Modeled on the FDX account model, which splits an account into a high-level
*category* (deposit / loan / investment / insurance) and a more specific *type*
(checking, mortgage, TFSA, …). We keep that two-level shape because it's how FDX
organizes balances and endpoints, and validate that the type actually belongs to
the category — a cheap check that catches a whole class of normalizer mistakes.

The type enumeration is a pragmatic, Canada-flavored subset of FDX's full list
(Wealthsimple's world: TFSA/RRSP/RESP/FHSA registered accounts), not the entire
specification.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import AwareDatetime, model_validator

from .balance import Balance
from .common import CurrencyCode, EntityId, FdxBaseModel


class AccountCategory(StrEnum):
    """FDX top-level account category."""

    DEPOSIT_ACCOUNT = "DEPOSIT_ACCOUNT"
    LOAN_ACCOUNT = "LOAN_ACCOUNT"
    INVESTMENT_ACCOUNT = "INVESTMENT_ACCOUNT"
    INSURANCE_ACCOUNT = "INSURANCE_ACCOUNT"


class AccountType(StrEnum):
    """Specific account type — a subset of FDX's enumeration.

    Grouped by the category each type belongs to (see ``CATEGORY_TYPES``).
    """

    # Deposit
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    MONEY_MARKET = "MONEY_MARKET"
    CD = "CD"
    PREPAID = "PREPAID"
    # Loan
    LOAN = "LOAN"
    MORTGAGE = "MORTGAGE"
    LINE_OF_CREDIT = "LINE_OF_CREDIT"
    CREDIT_CARD = "CREDIT_CARD"
    # Investment (Canada-flavored registered accounts included)
    BROKERAGE = "BROKERAGE"
    TFSA = "TFSA"
    RRSP = "RRSP"
    RESP = "RESP"
    FHSA = "FHSA"
    # Insurance
    ANNUITY = "ANNUITY"
    LIFE_INSURANCE = "LIFE_INSURANCE"


#: Which types are valid under each category. Used by the consistency validator.
CATEGORY_TYPES: dict[AccountCategory, frozenset[AccountType]] = {
    AccountCategory.DEPOSIT_ACCOUNT: frozenset(
        {
            AccountType.CHECKING,
            AccountType.SAVINGS,
            AccountType.MONEY_MARKET,
            AccountType.CD,
            AccountType.PREPAID,
        }
    ),
    AccountCategory.LOAN_ACCOUNT: frozenset(
        {
            AccountType.LOAN,
            AccountType.MORTGAGE,
            AccountType.LINE_OF_CREDIT,
            AccountType.CREDIT_CARD,
        }
    ),
    AccountCategory.INVESTMENT_ACCOUNT: frozenset(
        {
            AccountType.BROKERAGE,
            AccountType.TFSA,
            AccountType.RRSP,
            AccountType.RESP,
            AccountType.FHSA,
        }
    ),
    AccountCategory.INSURANCE_ACCOUNT: frozenset(
        {
            AccountType.ANNUITY,
            AccountType.LIFE_INSURANCE,
        }
    ),
}


class AccountStatus(StrEnum):
    """Lifecycle status of the account."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RESTRICTED = "RESTRICTED"
    PENDING_OPEN = "PENDING_OPEN"


class Account(FdxBaseModel):
    """A financial account owned by a customer at some institution."""

    account_id: EntityId
    #: Owning customer. Optional at the account level because some source feeds
    #: deliver accounts and customers separately; the normalizer links them.
    customer_id: EntityId | None = None

    category: AccountCategory
    account_type: AccountType
    status: AccountStatus = AccountStatus.OPEN
    currency: CurrencyCode

    #: Human-friendly label ("Joint Chequing") if the source provides one.
    nickname: str | None = None
    #: Masked/display account number, e.g. ``"****1234"``. Never the full number
    #: in the canonical model — data minimization starts at the schema.
    masked_number: str | None = None

    opened_at: AwareDatetime | None = None
    balances: list[Balance] = []

    @model_validator(mode="after")
    def _type_matches_category(self) -> Account:
        """Reject a type that doesn't belong to its category.

        e.g. a ``LOAN_ACCOUNT`` with type ``CHECKING`` is a normalization bug.
        """

        allowed = CATEGORY_TYPES[self.category]
        if self.account_type not in allowed:
            raise ValueError(
                f"account_type {self.account_type.value!r} is not valid for "
                f"category {self.category.value!r}"
            )
        return self
