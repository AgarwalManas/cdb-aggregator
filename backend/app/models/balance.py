"""Account balance — a point-in-time snapshot of value.

Modeled on FDX's account balance fields. Split out as its own canonical type
(rather than inlined on ``Account``) because an account can carry several
balances and the consent layer treats "balances" as its own data cluster that a
grant may or may not include.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import AwareDatetime, model_validator

from .common import CurrencyCode, FdxBaseModel, Money


class BalanceType(StrEnum):
    """Whether the balance represents something owned or owed.

    Mirrors FDX's asset/liability distinction: a deposit or investment account
    holds an ``ASSET`` balance, a loan or credit line a ``LIABILITY``.
    """

    ASSET = "ASSET"
    LIABILITY = "LIABILITY"


class Balance(FdxBaseModel):
    """A single balance reading for an account at ``as_of``."""

    as_of: AwareDatetime
    currency: CurrencyCode
    balance_type: BalanceType = BalanceType.ASSET

    #: The ledger balance. Signed: may be negative (overdraft, or a liability
    #: expressed as a negative asset by some sources before normalization).
    current: Money

    #: Funds actually available to spend, if the source distinguishes it from
    #: ``current`` (pending holds, uncleared deposits). Optional.
    available: Money | None = None

    @model_validator(mode="after")
    def _available_not_above_current(self) -> Balance:
        """For an asset balance, available funds can't exceed the ledger balance.

        A source reporting ``available > current`` on an asset is contradictory
        (you can't have more spendable than you hold); we reject it rather than
        pass the inconsistency downstream. ``available < current`` is normal
        (pending holds). The check is skipped for liabilities, where "available"
        means available *credit* — a genuinely different quantity.
        """

        if (
            self.balance_type is BalanceType.ASSET
            and self.available is not None
            and self.available > self.current
        ):
            raise ValueError("available balance cannot exceed current balance for an asset")
        return self
