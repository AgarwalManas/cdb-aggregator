"""Aggregation across connected sources (Item 10).

Builds the unified views — merged accounts, a merged transaction feed, and
household net worth — by reading every source **through the consent gate**. A
connection that isn't active, a scope that wasn't granted, or a balance that was
minimized away simply doesn't appear; nothing bypasses Phase 2.

Because these reads go through the same enforcing reader as everything else, they
are also logged to the traceability audit log — viewing your dashboard is itself
an auditable access.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.api.demo import AggregatorState
from app.api.dto import (
    AccountView,
    ExcludedAccount,
    NetWorthLine,
    NetWorthView,
    TransactionView,
)
from app.consent import ConsentDenied


def merged_accounts(state: AggregatorState, at: datetime | None = None) -> list[AccountView]:
    """Every account the customer has an active, in-scope connection for."""
    reader = state.reader()
    views: list[AccountView] = []
    seen: set[str] = set()
    for connection in state.connections:
        consent = state.store.get(connection.connection_id)
        if consent is None or not consent.is_active(at):
            continue
        for account_id in consent.account_ids:
            if account_id in seen:
                continue
            try:
                account = reader.read_account(state.customer_id, state.recipient, account_id, at=at)
            except ConsentDenied:
                continue
            seen.add(account_id)
            balance = account.balances[0] if account.balances else None
            views.append(
                AccountView(
                    account_id=account.account_id,
                    source_id=connection.source_id,
                    source_label=connection.source_label,
                    category=account.category.value,
                    account_type=account.account_type.value,
                    currency=account.currency,
                    nickname=account.nickname,
                    masked_number=account.masked_number,
                    balance_shared=balance is not None,
                    current=balance.current if balance else None,
                    balance_type=balance.balance_type.value if balance else None,
                )
            )
    return views


def merged_transactions(
    state: AggregatorState, at: datetime | None = None
) -> list[TransactionView]:
    """The merged, most-recent-first transaction feed across all sources."""
    reader = state.reader()
    rows: list[tuple[object, str]] = []
    for connection in state.connections:
        consent = state.store.get(connection.connection_id)
        if consent is None or not consent.is_active(at):
            continue
        for account_id in consent.account_ids:
            try:
                txns = reader.read_transactions(
                    state.customer_id, state.recipient, account_id, at=at
                )
            except ConsentDenied:
                continue
            rows.extend((txn, connection.source_label) for txn in txns)
    rows.sort(key=lambda r: r[0].transaction_timestamp, reverse=True)
    return [
        TransactionView(
            transaction_id=txn.transaction_id,
            account_id=txn.account_id,
            source_label=source_label,
            amount=txn.amount,
            currency=txn.currency,
            direction=txn.debit_credit_memo.value,
            description=txn.description,
            category=txn.category,
            occurred_at=txn.transaction_timestamp,
            status=txn.status.value,
        )
        for txn, source_label in rows
    ]


def net_worth(state: AggregatorState, at: datetime | None = None) -> NetWorthView:
    """Household net worth from the balances the customer actually shared.

    Accounts whose balance wasn't granted (minimized away) are surfaced as
    *excluded* rather than silently dropped — consent is visible, not hidden.
    """
    accounts = merged_accounts(state, at)
    assets = Decimal("0")
    liabilities = Decimal("0")
    currency = "CAD"
    included: list[NetWorthLine] = []
    excluded: list[ExcludedAccount] = []

    for account in accounts:
        if not account.balance_shared or account.current is None:
            excluded.append(
                ExcludedAccount(
                    account_id=account.account_id,
                    source_label=account.source_label,
                    reason="Balance not shared",
                )
            )
            continue
        currency = account.currency
        if account.balance_type == "ASSET":
            assets += account.current
        else:
            liabilities += account.current
        included.append(
            NetWorthLine(
                account_id=account.account_id,
                source_label=account.source_label,
                balance_type=account.balance_type or "ASSET",
                current=account.current,
            )
        )

    return NetWorthView(
        currency=currency,
        assets=assets,
        liabilities=liabilities,
        net_worth=assets - liabilities,
        member_name="Ada Lovelace",
        included=included,
        excluded=excluded,
    )
