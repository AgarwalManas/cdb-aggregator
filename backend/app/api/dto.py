"""API DTOs for the consent dashboard (Item 9).

Thin request/response shapes the React client consumes, kept separate from the
canonical domain model. They serialize as camelCase JSON (the client's idiom)
while staying pythonic in code.
"""

from __future__ import annotations

from datetime import datetime

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
    scope: ConsentScope
    account_id: str | None
    allowed: bool
    reason: str | None
    consent_id: str | None
    record_count: int
    withheld: list[str]


def scope_catalog() -> list[ScopeInfo]:
    return [
        ScopeInfo(scope=scope, label=label, description=desc)
        for scope, (label, desc) in SCOPE_CATALOG.items()
    ]
