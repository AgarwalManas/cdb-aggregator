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


class ChainEntryView(ApiModel):
    """One chain entry, with the exact fields that go into its hash (item-30).

    ``occurred_at`` is the literal ``isoformat()`` string the server hashed, so a
    browser can rebuild the preimage byte-for-byte and recompute the SHA-256 —
    the whole point is that the user doesn't have to trust the server's answer.
    """

    occurred_at: str
    action: str
    customer_id: str
    recipient: str
    scope: str
    allowed: bool
    account_id: str | None
    reason: str | None
    consent_id: str | None
    record_count: int
    withheld: list[str]
    prev_hash: str
    entry_hash: str


class ChainView(ApiModel):
    """The full hash chain, published so anyone can recompute it independently."""

    algorithm: str  # "SHA-256"
    genesis: str  # the seed prev-hash the first entry links to
    head: str  # the published chain head (latest entry hash)
    entries: list[ChainEntryView]


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


# --- Agent activity & authority console (item-28) ----------------------------


class AgentActivityRow(ApiModel):
    """One line in the agent's live action feed — a single logged read."""

    occurred_at: datetime
    intent: str  # human phrase: "Read current balance"
    action: str  # raw audit action, e.g. read_balances
    scope: ConsentScope
    account_id: str | None
    source_label: str | None
    authorizing_consent_id: str | None  # the grant this read relied on
    allowed: bool
    status: str  # "authorized" / "denied"


class AgentActivityView(ApiModel):
    """The agent's action feed plus whether it is currently able to act."""

    live: bool  # active delegation and not paused → the agent can act now
    halted_reason: str | None  # why the feed is halted (revoked / paused / expired / none)
    rows: list[AgentActivityRow]


class AuthorityView(ApiModel):
    """The scoped authority the agent holds right now — the authority card."""

    agent_id: str
    agent_name: str
    description: str
    status: str  # GRANTED / EXPIRED / REVOKED / NONE
    paused: bool
    scopes: list[ConsentScope]
    account_ids: list[str]
    created_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    seconds_remaining: int | None = None  # time left on the delegation, floored at 0


class ScopePreviewView(ApiModel):
    """Intent → scope preview: what a grant would and wouldn't let the agent see."""

    agent_name: str
    duration_days: int
    account_ids: list[str]
    account_count: int
    visible: list[ScopeInfo]  # scopes the delegation would grant
    withheld: list[ScopeInfo]  # scopes it would leave off — the agent stays blind to these


class ApprovalView(ApiModel):
    """A suggestion-only action awaiting the human's decision."""

    approval_id: str
    created_at: datetime
    status: str  # PENDING / APPROVED / REJECTED / CHANGES_REQUESTED
    note: str | None
    decided_at: datetime | None
    suggestion: SuggestionView


class ApprovalDecisionRequest(ApiModel):
    decision: str  # APPROVE / REJECT / REQUEST_CHANGES
    note: str | None = None


# --- Portable alias + consent-gated resolver (item-31) -----------------------


class AliasTargetView(ApiModel):
    """A routing target the alias points at (or could) — masked, never raw."""

    account_id: str
    source_label: str
    display: str  # e.g. "Legacy Bank ···· 4821"


class AliasResolutionRow(ApiModel):
    """One line of the resolution history: who resolved, and what they were told."""

    occurred_at: datetime
    requester: str
    allowed: bool
    disclosed: str  # "one-time routing token" | "nothing"
    reason: str | None


class AliasView(ApiModel):
    """The portable-address card: current target, where it can point, its history."""

    handle: str
    target: AliasTargetView
    created_at: datetime
    repointed_at: datetime | None
    options: list[AliasTargetView]  # connected accounts the alias can re-point to
    history: list[AliasResolutionRow]


class ResolveRequest(ApiModel):
    requester: str = "counterparty:acme-payments"


class ResolutionView(ApiModel):
    """What a counterparty gets back from a resolution — a token, or a reason."""

    allowed: bool
    handle: str
    routing_token: str | None
    disclosed: str
    reason: str | None


class ExchangeRequest(ApiModel):
    token: str


class RoutingCoordinatesView(ApiModel):
    """Coordinates revealed once, on redeeming a token — the settlement step."""

    institution: str
    transit: str
    masked_account: str
    source_label: str


class RepointRequest(ApiModel):
    account_id: str


# --- Access receipts + permission simulation (item-29) -----------------------


class ReceiptView(ApiModel):
    """An audit event reshaped as a consumer-legible access receipt."""

    receipt_id: str
    occurred_at: datetime
    accessor: str  # the raw recipient id
    accessor_label: str  # "The aggregator" / "The assistant" / a counterparty
    accessor_type: str  # aggregator / agent / counterparty / other
    purpose: str
    cluster: str  # the scope value
    cluster_label: str
    fields: list[str]  # the fields this cluster covers
    account_id: str | None
    authorizing_consent_id: str | None
    allowed: bool
    record_count: int
    withheld: list[str]  # human labels of the clusters minimized away
    why: str  # one-line "why this was accessed"


class FieldView(ApiModel):
    """One field a scope would expose, with an illustrative value."""

    cluster: str
    cluster_label: str
    name: str
    example: str


class PermissionSimulationRequest(ApiModel):
    scopes: list[ConsentScope]


class PermissionSimulationView(ApiModel):
    """What a candidate scope set would expose vs withhold, before granting."""

    scopes: list[ConsentScope]
    visible: list[FieldView]
    withheld: list[FieldView]


# --- Selective-disclosure attestations (item-32, simulated) ------------------


class FactView(ApiModel):
    """A fact you can prove without sharing the underlying data."""

    fact_id: str
    question: str
    disclosure: str


class AttestationView(ApiModel):
    """A signed attestation of a derived fact — the conclusion, not the data."""

    fact_id: str
    question: str
    claim: str
    holds: bool
    subject: str
    issuer: str
    issued_at: str  # isoformat string, exactly as signed
    algorithm: str
    key_id: str
    disclosure: str
    signature: str
    simulated: bool = True  # this is a demonstration, not a real ZK proof


class IssueAttestationRequest(ApiModel):
    fact_id: str


class VerifyAttestationRequest(ApiModel):
    attestation: AttestationView


class AttestationVerificationView(ApiModel):
    valid: bool
    reason: str
