"""Demo state for the consent dashboard (Item 9).

The aggregator has no database yet, so ``build_demo_state`` stands up an
in-memory world the dashboard can show and act on: a customer with three
*connections* (one per mock source), and a real audit trail produced by running
a handful of reads through the Item 7/8 enforcing reader — including one that is
denied, so the traceability view has something honest to display.

A "connection" is the aggregator's own concept: a data source the customer has
authorized, paired with the ``Consent`` that governs it. Each connection is
scoped to that source's account ids, so the gate enforces per-source access even
though every grant is to the same recipient (this aggregator).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.adapters.base import SourceAdapter
from app.consent import (
    AuditLog,
    ConsentDenied,
    ConsentEnforcingReader,
    ConsentGate,
    ConsentStore,
)
from app.models import (
    Account,
    AccountCategory,
    AccountType,
    Balance,
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

# Known sources the customer can connect (mock providers from Items 3, 4, 6).
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
    """Everything the consent API operates on."""

    store: ConsentStore
    audit: AuditLog
    connections: list[Connection]
    customer_id: str = CUSTOMER_ID
    recipient: str = RECIPIENT
    _seq: int = field(default=0, repr=False)

    def next_connection_id(self) -> str:
        self._seq += 1
        return f"con-{self._seq}"


# --- A compact aggregated view for seeding the audit trail --------------------


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


def _demo_accounts(now: datetime) -> list[Account]:
    def acct(account_id, category, atype, current) -> Account:
        return Account(
            account_id=account_id,
            customer_id=CUSTOMER_ID,
            category=category,
            account_type=atype,
            currency="CAD",
            balances=[Balance(as_of=now, currency="CAD", current=current)],
        )

    return [
        acct("acc-chq-001", AccountCategory.DEPOSIT_ACCOUNT, AccountType.CHECKING, "4210.55"),
        acct("acc-inv-001", AccountCategory.INVESTMENT_ACCOUNT, AccountType.TFSA, "11193.50"),
        acct("GB-CHQ-9981", AccountCategory.DEPOSIT_ACCOUNT, AccountType.CHECKING, "4210.55"),
        acct("****1234", AccountCategory.DEPOSIT_ACCOUNT, AccountType.CHECKING, "4210.55"),
    ]


class _DemoAdapter(SourceAdapter):
    """A stand-in aggregated source, only used to seed a realistic audit trail."""

    source_name = "demo"

    def __init__(self, now: datetime) -> None:
        self._now = now
        self._accounts = _demo_accounts(now)

    def get_customer(self) -> Customer:
        return _demo_customer()

    def get_accounts(self) -> list[Account]:
        return self._accounts

    def get_transactions(self, account_id: str) -> list[Transaction]:
        if account_id in ("acc-chq-001", "GB-CHQ-9981"):
            return [
                Transaction(
                    transaction_id=f"{account_id}-t1",
                    account_id=account_id,
                    amount="85.20",
                    currency="CAD",
                    debit_credit_memo=DebitCreditMemo.DEBIT,
                    status=TransactionStatus.POSTED,
                    transaction_timestamp=self._now,
                    posted_timestamp=self._now,
                    description="LOBLAWS #1234",
                )
            ]
        return []

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        if account_id == "acc-inv-001":
            return [
                InvestmentHolding(
                    holding_id="h-1",
                    account_id=account_id,
                    holding_type="ETF",
                    symbol="VFV",
                    quantity="50",
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
    audit = AuditLog()
    connections: list[Connection] = []

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
            ["acc-chq-001", "acc-inv-001"],
            90,
        ),
        (
            "legacy_bank",
            {ConsentScope.ACCOUNT_DETAILS, ConsentScope.BALANCES, ConsentScope.TRANSACTIONS},
            ["GB-CHQ-9981"],
            60,
        ),
        (
            "scraper_bank",
            {ConsentScope.ACCOUNT_DETAILS, ConsentScope.TRANSACTIONS},
            ["****1234"],
            5,
        ),
    ]
    state = AggregatorState(store=store, audit=audit, connections=connections)
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

    _seed_audit_trail(store, audit, now)
    return state


def _seed_audit_trail(store: ConsentStore, audit: AuditLog, now: datetime) -> None:
    """Run real reads through the enforcing reader to populate the audit log."""
    reader = ConsentEnforcingReader(_DemoAdapter(now), ConsentGate(store), audit=audit)
    reader.read_accounts(CUSTOMER_ID, RECIPIENT, at=now)
    reader.read_customer(CUSTOMER_ID, RECIPIENT, at=now)
    reader.read_transactions(CUSTOMER_ID, RECIPIENT, "acc-chq-001", at=now)
    reader.read_balances(CUSTOMER_ID, RECIPIENT, "GB-CHQ-9981", at=now)
    reader.read_holdings(CUSTOMER_ID, RECIPIENT, "acc-inv-001", at=now)
    # Denied: holdings on a legacy account — no active grant both covers that
    # account and includes the investments scope.
    try:
        reader.read_holdings(CUSTOMER_ID, RECIPIENT, "GB-CHQ-9981", at=now)
    except ConsentDenied:
        pass
