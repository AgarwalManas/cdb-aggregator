"""Traceability audit log — an append-only record of every data access.

Maps to FDX's **Traceability** principle: each read (allowed *or* denied) is
recorded against the consent that authorized it, so a customer — or an auditor —
can answer "who saw what, when, and under which grant?". Denied attempts are
logged too; an access that was blocked is exactly the kind of thing you want a
trail of.

The log is **append-only**: :meth:`AuditLog.record` is the only mutation, and
reads hand back immutable copies. A real deployment writes this to durable,
tamper-evident storage; the shape here is what matters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.models import ConsentScope

from .enforcement import DenialReason


@dataclass(frozen=True)
class AuditEvent:
    """One immutable access record."""

    occurred_at: datetime
    action: str  # the read attempted, e.g. "read_transactions"
    customer_id: str
    recipient: str
    scope: ConsentScope
    allowed: bool
    account_id: str | None = None
    reason: DenialReason | None = None  # set iff denied
    consent_id: str | None = None  # the grant relied on iff allowed
    record_count: int = 0  # how many records were disclosed
    withheld: tuple[str, ...] = field(default_factory=tuple)  # clusters minimized away


class AuditLog:
    """Append-only store of :class:`AuditEvent` records."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> AuditEvent:
        self._events.append(event)
        return event

    def all(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def for_customer(self, customer_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self._events if e.customer_id == customer_id)

    def for_consent(self, consent_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e for e in self._events if e.consent_id == consent_id)

    def __len__(self) -> int:
        return len(self._events)
