"""Access receipts + permission simulation (item-29).

Two consumer-legible views over machinery that already exists:

* **Access receipts** reshape each audit event (Item 8) into a plain-language
  receipt — who accessed what cluster, under which grant, for what purpose, what
  was disclosed vs withheld, and a one-line "why". Structure nods to ISO/IEC TS
  27560 / Kantara consent receipts.
* **Permission simulation** turns granting from a blind checkbox into an informed
  preview: for a candidate set of scopes, exactly which fields would be visible
  vs withheld, illustrated with values from the mock world.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.api.demo import RECIPIENT
from app.api.dto import SCOPE_CATALOG, FieldView, ReceiptView
from app.consent.audit import AuditEvent
from app.models import ConsentScope

#: What each read is *for*, in the customer's terms.
PURPOSE: dict[str, str] = {
    "read_accounts": "Show your accounts in one place",
    "read_account": "Check a specific account",
    "read_customer": "Show your profile",
    "read_balances": "Show a current balance",
    "read_transactions": "Show recent transactions",
    "read_holdings": "Show investment holdings",
    "resolve_alias": "Route a payment to your portable alias",
    "repoint_alias": "Re-point your portable alias",
}

#: Minimization clusters (from app.consent.minimize) → human labels.
CLUSTER_LABELS: dict[str, str] = {"contact": "Contact", "balances": "Balances"}

#: The concrete fields each scope governs, with an illustrative value. Examples
#: are representative of the mock world, framed as "what this field would hold".
FIELD_CATALOG: dict[ConsentScope, list[tuple[str, str]]] = {
    ConsentScope.ACCOUNT_DETAILS: [
        ("Account type", "Chequing"),
        ("Nickname", "Everyday Chequing"),
        ("Masked number", "···· 5822"),
        ("Currency", "CAD"),
    ],
    ConsentScope.BALANCES: [
        ("Current balance", "$4,210.55"),
        ("Available balance", "$4,180.55"),
    ],
    ConsentScope.TRANSACTIONS: [
        ("Merchant / description", "LOBLAWS #1234"),
        ("Amount", "$85.20"),
        ("Category", "Groceries"),
        ("Date", "2 days ago"),
    ],
    ConsentScope.INVESTMENT_HOLDINGS: [
        ("Holding", "VFV"),
        ("Quantity", "50 units"),
        ("Market value", "$5,512.50"),
    ],
    ConsentScope.CUSTOMER_IDENTITY: [
        ("Name", "Ada Lovelace"),
        ("Date of birth", "1815-12-10"),
    ],
    ConsentScope.CUSTOMER_CONTACT: [
        ("Email", "ada@example.com"),
        ("Phone", "+1 416 555 0134"),
        ("Address", "1 Analytical Way, Toronto"),
    ],
}


def _accessor(recipient: str) -> tuple[str, str]:
    """Classify who accessed, returning ``(type, label)``."""
    if recipient.startswith("agent:"):
        return "agent", "The assistant"
    if recipient.startswith("counterparty:"):
        return "counterparty", recipient.split(":", 1)[1]
    if recipient == RECIPIENT:
        return "aggregator", "The aggregator"
    return "other", recipient


def build_receipt(event: AuditEvent, index: int) -> ReceiptView:
    """Reshape one audit event into a plain-language access receipt."""
    accessor_type, accessor_label = _accessor(event.recipient)
    cluster_label = SCOPE_CATALOG[event.scope][0]
    fields = [name for name, _ in FIELD_CATALOG.get(event.scope, [])]
    withheld = [CLUSTER_LABELS.get(w, w.title()) for w in event.withheld]

    if event.allowed:
        why = (
            f"{accessor_label} read your {cluster_label.lower()} under an active grant"
            f"{f' ({event.consent_id})' if event.consent_id else ''}."
        )
    else:
        why = f"{accessor_label} was refused your {cluster_label.lower()} — {event.reason}."

    return ReceiptView(
        receipt_id=f"rcpt-{index + 1}",
        occurred_at=event.occurred_at,
        accessor=event.recipient,
        accessor_label=accessor_label,
        accessor_type=accessor_type,
        purpose=PURPOSE.get(event.action, event.action),
        cluster=event.scope.value,
        cluster_label=cluster_label,
        fields=fields,
        account_id=event.account_id,
        authorizing_consent_id=event.consent_id,
        allowed=event.allowed,
        record_count=event.record_count,
        withheld=withheld,
        why=why,
    )


def build_receipts(events: Iterable[AuditEvent]) -> list[ReceiptView]:
    """Every audit event as a receipt, newest first (ids stay chronological)."""
    receipts = [build_receipt(event, i) for i, event in enumerate(events)]
    return list(reversed(receipts))


def _fields_for(scope: ConsentScope) -> list[FieldView]:
    label = SCOPE_CATALOG[scope][0]
    return [
        FieldView(cluster=scope.value, cluster_label=label, name=name, example=example)
        for name, example in FIELD_CATALOG[scope]
    ]


def simulate_permission(scopes: Iterable[ConsentScope]) -> tuple[list[FieldView], list[FieldView]]:
    """For a candidate scope set, the fields that would be visible vs withheld."""
    granted = set(scopes)
    visible: list[FieldView] = []
    withheld: list[FieldView] = []
    for scope in FIELD_CATALOG:
        (visible if scope in granted else withheld).extend(_fields_for(scope))
    return visible, withheld
