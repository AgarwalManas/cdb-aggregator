"""API DTOs for the consent dashboard (Item 9).

Thin request/response shapes the React client consumes, kept separate from the
canonical domain model. They serialize as camelCase JSON (the client's idiom)
while staying pythonic in code.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models import ConsentScope


class ApiModel(BaseModel):
    """Base for API DTOs: camelCase on the wire, snake_case in code."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


#: Human-friendly labels for each scope, shown as chips in the dashboard.
SCOPE_CATALOG: dict[ConsentScope, tuple[str, str]] = {
    ConsentScope.ACCOUNT_DETAILS: ("Account details", "Account names, types, and masked numbers"),
    ConsentScope.BALANCES: ("Balances", "Current and available balances"),
    ConsentScope.TRANSACTIONS: ("Transactions", "Transaction history"),
    ConsentScope.INVESTMENT_HOLDINGS: ("Investments", "Holdings and market values"),
    ConsentScope.CUSTOMER_IDENTITY: ("Identity", "Name and date of birth"),
    ConsentScope.CUSTOMER_CONTACT: ("Contact", "Email, phone, and address"),
}


class ScopeInfo(ApiModel):
    scope: ConsentScope
    label: str
    description: str


class ConnectionView(ApiModel):
    """A connected data source and the consent governing it."""

    connection_id: str
    source_id: str
    source_label: str
    status: str  # effective status, clock-aware: GRANTED / EXPIRED / REVOKED / PENDING
    scopes: list[ConsentScope]
    account_ids: list[str]
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class GrantRequest(ApiModel):
    source_id: str
    scopes: list[ConsentScope]
    duration_days: int = 90
    account_ids: list[str] = []


class AuditEventView(ApiModel):
    """One row in the traceability log."""

    occurred_at: datetime
    action: str
    recipient: str  # who accessed — the aggregator or a delegated agent
    scope: ConsentScope
    account_id: str | None
    allowed: bool
    reason: str | None
    consent_id: str | None
    record_count: int
    withheld: list[str]


class ChainVerificationView(ApiModel):
    """Result of verifying the audit log's tamper-evident hash chain (item-22)."""

    valid: bool
    checked: int  # number of entries walked
    broken_at: int | None = None  # index of the first broken entry, if any


class ComparisonRow(ApiModel):
    """One dimension contrasting screen-scraping with FDX open banking (item-20)."""

    dimension: str
    screen_scraping: str
    fdx_open_banking: str


def scope_catalog() -> list[ScopeInfo]:
    return [
        ScopeInfo(scope=scope, label=label, description=desc)
        for scope, (label, desc) in SCOPE_CATALOG.items()
    ]


# --- Aggregation views (Item 10) ---------------------------------------------


class AccountView(ApiModel):
    """A merged account, tagged with the source it came from."""

    account_id: str
    source_id: str
    source_label: str
    category: str
    account_type: str
    currency: str
    nickname: str | None
    masked_number: str | None
    balance_shared: bool  # False when BALANCES wasn't granted (minimized away)
    current: Decimal | None
    balance_type: str | None


class TransactionView(ApiModel):
    """One row in the merged transaction feed."""

    transaction_id: str
    account_id: str
    source_label: str
    amount: Decimal
    currency: str
    direction: str  # DEBIT / CREDIT
    description: str | None
    category: str | None
    occurred_at: datetime
    status: str


class NetWorthLine(ApiModel):
    account_id: str
    source_label: str
    balance_type: str
    current: Decimal


class ExcludedAccount(ApiModel):
    account_id: str
    source_label: str
    reason: str


class NetWorthView(ApiModel):
    """Household net worth, computed only from balances the customer shared."""

    currency: str
    assets: Decimal
    liabilities: Decimal
    net_worth: Decimal
    member_name: str
    included: list[NetWorthLine]
    excluded: list[ExcludedAccount]


# --- Agentic delegation (Item 11) --------------------------------------------


class DelegationView(ApiModel):
    """The task delegated to the agent, and the consent governing it."""

    agent_id: str
    agent_name: str
    description: str
    status: str  # GRANTED / EXPIRED / REVOKED / NONE
    scopes: list[ConsentScope]
    account_ids: list[str]
    created_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


class AnalyzedAccountView(ApiModel):
    account_id: str
    label: str
    source_label: str | None
    balance: Decimal
    rate: Decimal
    idle: Decimal
    estimated_gain: Decimal


class NotCountedView(ApiModel):
    account_id: str
    reason: str


class SuggestionView(ApiModel):
    """The agent's advisory output — a suggestion, never an action."""

    idle_cash: Decimal
    currency: str
    estimated_annual_gain: Decimal
    target_rate: Decimal
    threshold_rate: Decimal
    analyzed: list[AnalyzedAccountView]
    not_counted: list[NotCountedView]
    advisory: str = "This is a suggestion. Nothing was moved — the assistant has read-only access."
