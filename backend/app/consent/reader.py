"""The consent-enforcing reader — where policy, traceability, and control meet.

Wraps any Item 5 :class:`~app.adapters.base.SourceAdapter` and makes every read:

1. **pass the consent gate** (Item 7) — active, in-scope, account-covering grant,
2. **get logged** to the append-only audit log (Item 8, Traceability) — allowed
   or denied, tied to the grant it relied on,
3. **come back minimized** (Item 8, Control) — only the fields the granted scopes
   permit (contact withheld without ``CUSTOMER_CONTACT``; balances withheld
   without ``BALANCES``).

This is the single choke point later HTTP endpoints (Items 9-10) depend on rather
than touching adapters directly.

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
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.adapters.base import SourceAdapter
from app.models import (
    Account,
    Balance,
    ConsentScope,
    Customer,
    InvestmentHolding,
    Transaction,
)

from .audit import AuditEvent, AuditLog
from .enforcement import ConsentDecision, ConsentDenied, ConsentGate
from .minimize import minimize_account, minimize_customer


class ConsentEnforcingReader:
    """Reads from a source only for what an active, in-scope consent permits."""

    def __init__(
        self, adapter: SourceAdapter, gate: ConsentGate, audit: AuditLog | None = None
    ) -> None:
        self._adapter = adapter
        self._gate = gate
        self._audit = audit

    # --- public reads --------------------------------------------------------

    def read_customer(
        self, customer_id: str, recipient: str, *, at: datetime | None = None
    ) -> Customer:
        decision = self._authorize(
            "read_customer", customer_id, recipient, ConsentScope.CUSTOMER_IDENTITY, None, at
        )
        customer, withheld = minimize_customer(
            self._adapter.get_customer(), decision.consent.scopes
        )
        self._log("read_customer", customer_id, recipient, decision, at, 1, withheld)
        return customer

    def read_accounts(
        self, customer_id: str, recipient: str, *, at: datetime | None = None
    ) -> list[Account]:
        decision = self._authorize(
            "read_accounts", customer_id, recipient, ConsentScope.ACCOUNT_DETAILS, None, at
        )
        scopes = decision.consent.scopes
        minimized = [minimize_account(a, scopes) for a in self._adapter.get_accounts()]
        accounts = [a for a, _ in minimized]
        withheld = minimized[0][1] if minimized else ()
        self._log("read_accounts", customer_id, recipient, decision, at, len(accounts), withheld)
        return accounts

    def read_account(
        self, customer_id: str, recipient: str, account_id: str, *, at: datetime | None = None
    ) -> Account:
        """A single account, gated on ``ACCOUNT_DETAILS`` + coverage of that account.

        The account-scoped counterpart of :meth:`read_accounts`; aggregation
        (Item 10) uses it so each source's accounts are checked individually.
        """
        decision = self._authorize(
            "read_account", customer_id, recipient, ConsentScope.ACCOUNT_DETAILS, account_id, at
        )
        account, withheld = minimize_account(
            self._find_account(account_id), decision.consent.scopes
        )
        self._log("read_account", customer_id, recipient, decision, at, 1, withheld)
        return account

    def read_balances(
        self, customer_id: str, recipient: str, account_id: str, *, at: datetime | None = None
    ) -> list[Balance]:
        decision = self._authorize(
            "read_balances", customer_id, recipient, ConsentScope.BALANCES, account_id, at
        )
        balances = self._find_account(account_id).balances
        self._log("read_balances", customer_id, recipient, decision, at, len(balances), ())
        return balances

    def read_transactions(
        self, customer_id: str, recipient: str, account_id: str, *, at: datetime | None = None
    ) -> list[Transaction]:
        decision = self._authorize(
            "read_transactions", customer_id, recipient, ConsentScope.TRANSACTIONS, account_id, at
        )
        txns = self._adapter.get_transactions(account_id)
        self._log("read_transactions", customer_id, recipient, decision, at, len(txns), ())
        return txns

    def read_holdings(
        self, customer_id: str, recipient: str, account_id: str, *, at: datetime | None = None
    ) -> list[InvestmentHolding]:
        decision = self._authorize(
            "read_holdings",
            customer_id,
            recipient,
            ConsentScope.INVESTMENT_HOLDINGS,
            account_id,
            at,
        )
        holdings = self._adapter.get_holdings(account_id)
        self._log("read_holdings", customer_id, recipient, decision, at, len(holdings), ())
        return holdings

    # --- internals -----------------------------------------------------------

    def _authorize(
        self,
        action: str,
        customer_id: str,
        recipient: str,
        scope: ConsentScope,
        account_id: str | None,
        at: datetime | None,
    ) -> ConsentDecision:
        """Gate the read; log + raise on denial, return the decision on allow."""
        decision = self._gate.check(customer_id, recipient, scope, account_id=account_id, at=at)
        if not decision.allowed or decision.consent is None:
            self._log(action, customer_id, recipient, decision, at, 0, ())
            raise ConsentDenied(decision)
        return decision

    def _log(
        self,
        action: str,
        customer_id: str,
        recipient: str,
        decision: ConsentDecision,
        at: datetime | None,
        record_count: int,
        withheld: tuple[str, ...],
    ) -> None:
        if self._audit is None:
            return
        self._audit.record(
            AuditEvent(
                occurred_at=at or datetime.now(UTC),
                action=action,
                customer_id=customer_id,
                recipient=recipient,
                scope=decision.scope,
                allowed=decision.allowed,
                account_id=decision.account_id,
                reason=decision.reason,
                consent_id=decision.consent.consent_id if decision.consent else None,
                record_count=record_count,
                withheld=withheld,
            )
        )

    def _find_account(self, account_id: str) -> Account:
        for account in self._adapter.get_accounts():
            if account.account_id == account_id:
                return account
        raise KeyError(account_id)
