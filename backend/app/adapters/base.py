"""The common adapter interface and shared normalization helpers.

Every source — the clean FDX bank, the messy legacy bank, and anything added
later — is reached through the same :class:`SourceAdapter`, which returns
**canonical** model objects (``app.models``). That uniformity is the whole point
of this layer: downstream code (the consent gate in Item 7, the dashboards in
Items 9-10) works against one shape and never sees a source's quirks.

The design separates two concerns:

* **Transport** — a :class:`SourceClient` fetches *raw* dicts from a source
  (HTTP, auth, pagination). Each source ships its own.
* **Mapping** — pure functions turn a raw dict into a canonical model. These are
  where schema drift is tamed, and they're unit-tested directly (no network).

An adapter is just a ``SourceClient`` + the source's mappers, wired behind the
common interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol, runtime_checkable

from app.models import (
    Account,
    AccountCategory,
    Customer,
    InvestmentHolding,
    Transaction,
)


class NormalizationError(Exception):
    """Raised when a raw record can't be mapped into the canonical model.

    Carries enough context (which source, which entity, which id) to make a bad
    upstream record actionable instead of a bare ``ValidationError`` deep in a
    stack trace.
    """

    def __init__(self, source: str, entity: str, identifier: object, cause: Exception) -> None:
        self.source = source
        self.entity = entity
        self.identifier = identifier
        self.cause = cause
        super().__init__(f"[{source}] could not normalize {entity} {identifier!r}: {cause}")


@runtime_checkable
class SourceClient(Protocol):
    """Transport contract: fetch *raw* (source-shaped) dicts. No mapping here."""

    def get_customer(self) -> dict[str, Any]: ...
    def get_accounts(self) -> list[dict[str, Any]]: ...
    def get_account(self, account_id: str) -> dict[str, Any]: ...
    def get_transactions(self, account_id: str) -> list[dict[str, Any]]: ...
    def get_holdings(self, account_id: str) -> list[dict[str, Any]]: ...


@dataclass
class SourceSnapshot:
    """A full, normalized pull from one source — the unit the aggregator merges."""

    source: str
    customer: Customer
    accounts: list[Account]
    transactions: dict[str, list[Transaction]]
    holdings: dict[str, list[InvestmentHolding]]


class SourceAdapter(ABC):
    """Maps one source into canonical models behind a uniform interface."""

    #: Stable identifier for the source (used in logs, audit trail, snapshots).
    source_name: str

    @abstractmethod
    def get_customer(self) -> Customer: ...

    @abstractmethod
    def get_accounts(self) -> list[Account]: ...

    @abstractmethod
    def get_transactions(self, account_id: str) -> list[Transaction]: ...

    @abstractmethod
    def get_holdings(self, account_id: str) -> list[InvestmentHolding]: ...

    def snapshot(self) -> SourceSnapshot:
        """Pull and normalize everything this source exposes.

        Holdings are only fetched for investment accounts — the one place the
        common interface reads the canonical category to avoid pointless calls.
        """

        accounts = self.get_accounts()
        transactions = {a.account_id: self.get_transactions(a.account_id) for a in accounts}
        holdings = {
            a.account_id: self.get_holdings(a.account_id)
            for a in accounts
            if a.category is AccountCategory.INVESTMENT_ACCOUNT
        }
        return SourceSnapshot(
            source=self.source_name,
            customer=self.get_customer(),
            accounts=accounts,
            transactions=transactions,
            holdings=holdings,
        )


# --- Shared parsing helpers --------------------------------------------------


def to_decimal(value: object) -> Decimal:
    """Parse money to ``Decimal`` from a number or a messy string.

    Tolerates thousands separators and a currency symbol (``"4,210.55"``,
    ``"$12.00"``) so source-specific quirks don't each reinvent this.
    """

    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(",", "").replace("$", "")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"not a decimal: {value!r}") from exc


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO-8601 timestamp, accepting a trailing ``Z`` for UTC."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize(source: str, entity: str, identifier: object, fn: Callable[[Any], Any], raw: Any):
    """Run a mapper, wrapping any failure as a :class:`NormalizationError`."""
    try:
        return fn(raw)
    except NormalizationError:
        raise
    except Exception as exc:
        raise NormalizationError(source, entity, identifier, exc) from exc
