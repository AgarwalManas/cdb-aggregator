"""The consent-enforcing reader — where policy meets data.

Wraps any Item 5 :class:`~app.adapters.base.SourceAdapter` and puts the consent
gate in front of every read. Nothing reaches a caller without first clearing an
active, in-scope grant, so this is the single choke point later HTTP endpoints
(Items 9-10) depend on rather than touching adapters directly.

Each read maps to the scope it requires:

======================  ===========================
Read                    Required scope
======================  ===========================
customer                ``CUSTOMER_IDENTITY``
accounts                ``ACCOUNT_DETAILS``
balances (per account)  ``BALANCES``
transactions            ``TRANSACTIONS``
holdings                ``INVESTMENT_HOLDINGS``
======================  ===========================

Account-scoped reads (balances, transactions, holdings) also require the grant
to cover that specific account. Field-level minimization *within* a granted
scope is Item 8's job; this item gates access at the read/cluster level.
"""

from __future__ import annotations

from datetime import datetime

from app.adapters.base import SourceAdapter
from app.models import (
    Account,
    Balance,
    ConsentScope,
    Customer,
    InvestmentHolding,
    Transaction,
)

from .enforcement import ConsentGate


class ConsentEnforcingReader:
    """Reads from a source only for what an active, in-scope consent permits."""

    def __init__(self, adapter: SourceAdapter, gate: ConsentGate) -> None:
        self._adapter = adapter
        self._gate = gate

    def read_customer(
        self, customer_id: str, recipient: str, *, at: datetime | None = None
    ) -> Customer:
        self._gate.authorize(customer_id, recipient, ConsentScope.CUSTOMER_IDENTITY, at=at)
        return self._adapter.get_customer()

    def read_accounts(
        self, customer_id: str, recipient: str, *, at: datetime | None = None
    ) -> list[Account]:
        self._gate.authorize(customer_id, recipient, ConsentScope.ACCOUNT_DETAILS, at=at)
        return self._adapter.get_accounts()

    def read_balances(
        self, customer_id: str, recipient: str, account_id: str, *, at: datetime | None = None
    ) -> list[Balance]:
        self._gate.authorize(
            customer_id, recipient, ConsentScope.BALANCES, account_id=account_id, at=at
        )
        account = self._find_account(account_id)
        return account.balances

    def read_transactions(
        self, customer_id: str, recipient: str, account_id: str, *, at: datetime | None = None
    ) -> list[Transaction]:
        self._gate.authorize(
            customer_id, recipient, ConsentScope.TRANSACTIONS, account_id=account_id, at=at
        )
        return self._adapter.get_transactions(account_id)

    def read_holdings(
        self, customer_id: str, recipient: str, account_id: str, *, at: datetime | None = None
    ) -> list[InvestmentHolding]:
        self._gate.authorize(
            customer_id, recipient, ConsentScope.INVESTMENT_HOLDINGS, account_id=account_id, at=at
        )
        return self._adapter.get_holdings(account_id)

    def _find_account(self, account_id: str) -> Account:
        for account in self._adapter.get_accounts():
            if account.account_id == account_id:
                return account
        raise KeyError(account_id)
