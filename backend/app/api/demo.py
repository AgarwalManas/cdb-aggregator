"""Demo state for the dashboards (Items 9-10).

The aggregator has no database yet, so ``build_demo_state`` stands up an
in-memory world the dashboards read and act on:

* a customer with **three connections** (one per mock source), each scoped to
  that source's accounts;
* an **aggregated set of accounts** across those sources — chequing + TFSA + a
  credit card at the FDX bank, savings at the legacy bank, and a mortgage at the
  scraped bank — spanning assets and liabilities so net worth is interesting;
* a real audit trail from running reads through the Item 7/8 enforcing reader,
  including one **denied** read.

Note the scraped connection is granted ``ACCOUNT_DETAILS`` + ``TRANSACTIONS`` but
**not** ``BALANCES`` — so the mortgage balance is withheld and drops out of net
worth, demonstrating that consent, not just connectivity, decides what you see.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.adapters.base import SourceAdapter
from app.agent import AGENT_ID, REQUIRED_SCOPES, run_cash_finder
from app.consent import (
    AuditLog,
    ConsentDenied,
    ConsentEnforcingReader,
    ConsentGate,
    ConsentStore,
    SqliteAuditLog,
    create_audit_log,
)
from app.core.config import get_settings
from app.models import (
    Account,
    AccountCategory,
    AccountType,
    Balance,
    BalanceType,
    ConsentScope,
    Customer,
    DebitCreditMemo,
    InvestmentHolding,
    PersonName,
    PostalAddress,
    Transaction,
    TransactionStatus,
)

CUSTOMER_ID = "cust-001"
RECIPIENT = "cdb-aggregator"

SOURCES: dict[str, str] = {
    "mock_fdx_bank": "Mock FDX Bank",
    "legacy_bank": "Legacy Bank",
    "scraper_bank": "OldBank (scraped)",
}


@dataclass
class Connection:
    """A connected source + the id of the consent governing it."""

    connection_id: str
    source_id: str
    source_label: str


@dataclass
class AggregatorState:
    """Everything the dashboards operate on."""

    store: ConsentStore
    audit: AuditLog | SqliteAuditLog
    connections: list[Connection]
    adapter: SourceAdapter
    customer_id: str = CUSTOMER_ID
    recipient: str = RECIPIENT
    agent_delegation_id: str | None = None
    _seq: int = field(default=0, repr=False)

    def next_connection_id(self) -> str:
        self._seq += 1
        return f"con-{self._seq}"

    def reader(self) -> ConsentEnforcingReader:
        """A consent-enforcing reader over the aggregated source + audit log."""
        return ConsentEnforcingReader(self.adapter, ConsentGate(self.store), self.audit)

    def connection_for_account(self, account_id: str) -> Connection | None:
        for connection in self.connections:
            consent = self.store.get(connection.connection_id)
            if consent is not None and account_id in consent.account_ids:
                return connection
        return None

    def balance_shared_account_ids(self, at: datetime | None = None) -> list[str]:
        """Accounts the aggregator holds balances for — the most the agent can get.

        The customer can only delegate to an agent what they themselves shared
        with the aggregator, so a delegation is capped at these accounts.
        """
        ids: list[str] = []
        for connection in self.connections:
            consent = self.store.get(connection.connection_id)
            if consent is None or not consent.is_active(at):
                continue
            if ConsentScope.BALANCES in consent.scopes:
                ids.extend(a for a in consent.account_ids if a not in ids)
        return ids


def _demo_customer() -> Customer:
    return Customer(
        customer_id=CUSTOMER_ID,
        name=PersonName(first="Ada", last="Lovelace"),
        emails=["ada@example.com"],
        addresses=[
            PostalAddress(
                line1="1 Analytical Way", city="Toronto", postal_code="M5V 1A1", country="CA"
            )
        ],
    )


def _account(account_id, category, atype, current, balance_type, now) -> Account:
    return Account(
        account_id=account_id,
        customer_id=CUSTOMER_ID,
        category=category,
        account_type=atype,
        currency="CAD",
        nickname={
            "fdx-chq": "Everyday Chequing",
            "fdx-tfsa": "Self-Directed TFSA",
            "fdx-visa": "Rewards Visa",
            "leg-sav": "Rainy Day Savings",
            "old-mortgage": "Home Mortgage",
        }.get(account_id),
        balances=[Balance(as_of=now, currency="CAD", current=current, balance_type=balance_type)],
    )


def _demo_accounts(now: datetime) -> list[Account]:
    A, L = BalanceType.ASSET, BalanceType.LIABILITY
    DEP, INV, LOAN = (
        AccountCategory.DEPOSIT_ACCOUNT,
        AccountCategory.INVESTMENT_ACCOUNT,
        AccountCategory.LOAN_ACCOUNT,
    )
    return [
        _account("fdx-chq", DEP, AccountType.CHECKING, "4210.55", A, now),
        _account("fdx-tfsa", INV, AccountType.TFSA, "11193.50", A, now),
        _account("fdx-visa", LOAN, AccountType.CREDIT_CARD, "1875.40", L, now),
        _account("leg-sav", DEP, AccountType.SAVINGS, "15800.00", A, now),
        _account("old-mortgage", LOAN, AccountType.MORTGAGE, "312000.00", L, now),
    ]


def _txn(txn_id, account_id, amount, memo, desc, category, when) -> Transaction:
    return Transaction(
        transaction_id=txn_id,
        account_id=account_id,
        amount=amount,
        currency="CAD",
        debit_credit_memo=memo,
        status=TransactionStatus.POSTED,
        transaction_timestamp=when,
        posted_timestamp=when,
        description=desc,
        category=category,
    )


class _DemoAdapter(SourceAdapter):
    """The aggregated canonical source the dashboards read (via the gate)."""

    source_name = "demo"

    def __init__(self, now: datetime) -> None:
        self._now = now
        self._accounts = _demo_accounts(now)
        D, C = DebitCreditMemo.DEBIT, DebitCreditMemo.CREDIT
        self._txns: dict[str, list[Transaction]] = {
            "fdx-chq": [
                _txn(
                    "fdx-chq-1",
                    "fdx-chq",
                    "2400.00",
                    C,
                    "PAYROLL DEPOSIT",
                    "Income",
                    now - timedelta(days=1),
                ),
                _txn(
                    "fdx-chq-2",
                    "fdx-chq",
                    "85.20",
                    D,
                    "LOBLAWS #1234",
                    "Groceries",
                    now - timedelta(days=2),
                ),
            ],
            "fdx-tfsa": [
                _txn(
                    "fdx-tfsa-1",
                    "fdx-tfsa",
                    "1000.00",
                    C,
                    "TFSA CONTRIBUTION",
                    "Transfer",
                    now - timedelta(days=5),
                ),
            ],
            "fdx-visa": [
                _txn(
                    "fdx-visa-1",
                    "fdx-visa",
                    "42.99",
                    D,
                    "UBER EATS",
                    "Restaurants",
                    now - timedelta(hours=6),
                ),
            ],
            "leg-sav": [
                _txn(
                    "leg-sav-1",
                    "leg-sav",
                    "12.33",
                    C,
                    "INTEREST",
                    "Interest",
                    now - timedelta(days=1),
                ),
            ],
            "old-mortgage": [
                _txn(
                    "old-mortgage-1",
                    "old-mortgage",
                    "1800.00",
                    D,
                    "MORTGAGE PAYMENT",
                    "Housing",
                    now - timedelta(days=3),
                ),
            ],
        }

    def get_customer(self) -> Customer:
        return _demo_customer()

    def get_accounts(self) -> list[Account]:
        return self._accounts

    def get_transactions(self, account_id: str) -> list[Transaction]:
        return self._txns.get(account_id, [])

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        if account_id == "fdx-tfsa":
            return [
                InvestmentHolding(
                    holding_id="fdx-tfsa-vfv",
                    account_id=account_id,
                    holding_type="ETF",
                    symbol="VFV",
                    quantity="50",
                    current_unit_price="110.25",
                    market_value="5512.50",
                    currency="CAD",
                    as_of=self._now,
                )
            ]
        return []


def build_demo_state(now: datetime | None = None) -> AggregatorState:
    """Seed three connections and a mixed (allowed + denied) audit trail."""
    now = now or datetime.now(UTC)
    store = ConsentStore()
    audit = create_audit_log(get_settings())
    connections: list[Connection] = []
    state = AggregatorState(
        store=store, audit=audit, connections=connections, adapter=_DemoAdapter(now)
    )

    seeds = [
        (
            "mock_fdx_bank",
            {
                ConsentScope.ACCOUNT_DETAILS,
                ConsentScope.BALANCES,
                ConsentScope.TRANSACTIONS,
                ConsentScope.INVESTMENT_HOLDINGS,
                ConsentScope.CUSTOMER_IDENTITY,
                ConsentScope.CUSTOMER_CONTACT,
            },
            ["fdx-chq", "fdx-tfsa", "fdx-visa"],
            90,
        ),
        (
            "legacy_bank",
            {ConsentScope.ACCOUNT_DETAILS, ConsentScope.BALANCES, ConsentScope.TRANSACTIONS},
            ["leg-sav"],
            60,
        ),
        # No BALANCES: the mortgage balance is withheld, so it drops out of net worth.
        (
            "scraper_bank",
            {ConsentScope.ACCOUNT_DETAILS, ConsentScope.TRANSACTIONS},
            ["old-mortgage"],
            5,
        ),
    ]
    for source_id, scopes, account_ids, days in seeds:
        connection_id = state.next_connection_id()
        store.grant(
            CUSTOMER_ID,
            RECIPIENT,
            scopes,
            duration=timedelta(days=days),
            account_ids=account_ids,
            now=now,
            consent_id=connection_id,
        )
        connections.append(Connection(connection_id, source_id, SOURCES[source_id]))

    _seed_audit_trail(state, now)
    _seed_agent_delegation(state, now)
    return state


def _seed_agent_delegation(state: AggregatorState, now: datetime) -> None:
    """Delegate the idle-cash task to the agent and run it once (for the trail)."""
    account_ids = state.balance_shared_account_ids(now)
    consent = state.store.grant(
        state.customer_id,
        AGENT_ID,  # the agent identity is the recipient of this grant
        REQUIRED_SCOPES,
        duration=timedelta(days=30),
        account_ids=account_ids,
        now=now,
        consent_id="agent-del-1",
    )
    state.agent_delegation_id = consent.consent_id
    # Run once so the traceability log opens showing the agent's (logged) access.
    run_cash_finder(
        state.reader(),
        customer_id=state.customer_id,
        account_ids=account_ids,
        source_label=lambda aid: (
            c.source_label if (c := state.connection_for_account(aid)) else None
        ),
        at=now,
    )


def _seed_audit_trail(state: AggregatorState, now: datetime) -> None:
    """A few real reads so the traceability log opens with honest history."""
    reader = state.reader()
    reader.read_accounts(CUSTOMER_ID, RECIPIENT, at=now)
    reader.read_customer(CUSTOMER_ID, RECIPIENT, at=now)
    reader.read_transactions(CUSTOMER_ID, RECIPIENT, "fdx-chq", at=now)
    reader.read_balances(CUSTOMER_ID, RECIPIENT, "leg-sav", at=now)
    reader.read_holdings(CUSTOMER_ID, RECIPIENT, "fdx-tfsa", at=now)
    # Denied: holdings on the savings account — no active grant both covers it
    # and includes the investments scope.
    try:
        reader.read_holdings(CUSTOMER_ID, RECIPIENT, "leg-sav", at=now)
    except ConsentDenied:
        pass
