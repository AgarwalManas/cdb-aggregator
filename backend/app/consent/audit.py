"""Traceability audit log — an append-only record of every data access.

Maps to FDX's **Traceability** principle: each read (allowed *or* denied) is
recorded against the consent that authorized it, so a customer — or an auditor —
can answer "who saw what, when, and under which grant?". Denied attempts are
logged too; an access that was blocked is exactly the kind of thing you want a
trail of.

The log is **append-only**: :meth:`AuditLog.record` is the only mutation, and
reads hand back immutable copies.

It is also **tamper-evident** (item-22). Each entry is bound into a hash chain:
its hash is computed over its own content *and the previous entry's hash*, so
altering or deleting any earlier entry changes every hash after it and
:meth:`AuditLog.verify` catches the break. That upgrades the log from
append-only *by convention* to append-only *with proof*. A production system
would additionally anchor the head hash in durable, external storage (see the
threat-model note); here the chain and its verification are what matter.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from app.models import ConsentScope

from .enforcement import DenialReason

#: The chain's starting point — the "previous hash" of the very first entry.
GENESIS_HASH = "0" * 64  # sha-256 hex width


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


@dataclass(frozen=True)
class ChainedEntry:
    """An :class:`AuditEvent` bound into the tamper-evident hash chain."""

    event: AuditEvent
    prev_hash: str  # entry_hash of the entry before it (GENESIS_HASH for the first)
    entry_hash: str  # sha-256 over this event's content + prev_hash


@dataclass(frozen=True)
class ChainVerification:
    """The result of re-walking the chain end to end."""

    valid: bool
    checked: int  # number of entries verified
    broken_at: int | None = None  # index of the first entry that failed, if any


def hash_event(event: AuditEvent, prev_hash: str) -> str:
    """Compute an entry's hash from a stable serialization of its content + prev_hash."""
    payload = "|".join(
        (
            prev_hash,
            event.occurred_at.isoformat(),
            event.action,
            event.customer_id,
            event.recipient,
            event.scope.value,
            "1" if event.allowed else "0",
            event.account_id or "",
            event.reason.value if event.reason else "",
            event.consent_id or "",
            str(event.record_count),
            ",".join(event.withheld),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_chain(entries: Sequence[ChainedEntry]) -> ChainVerification:
    """Re-walk a sequence of chained entries; report intactness and first break.

    Shared by every audit backend so the tamper-evidence check is defined once.
    """
    prev = GENESIS_HASH
    for index, entry in enumerate(entries):
        if entry.prev_hash != prev or entry.entry_hash != hash_event(entry.event, prev):
            return ChainVerification(valid=False, checked=len(entries), broken_at=index)
        prev = entry.entry_hash
    return ChainVerification(valid=True, checked=len(entries))


class AuditLog:
    """Append-only, hash-chained store of :class:`AuditEvent` records."""

    def __init__(self) -> None:
        self._entries: list[ChainedEntry] = []

    def record(self, event: AuditEvent) -> AuditEvent:
        prev_hash = self.head()
        self._entries.append(ChainedEntry(event, prev_hash, hash_event(event, prev_hash)))
        return event

    def head(self) -> str:
        """The current chain head — the last entry's hash, or GENESIS if empty."""
        return self._entries[-1].entry_hash if self._entries else GENESIS_HASH

    def chain(self) -> tuple[ChainedEntry, ...]:
        return tuple(self._entries)

    def verify(self) -> ChainVerification:
        """Re-walk the chain; report whether it's intact and where it first broke."""
        return verify_chain(self._entries)

    def all(self) -> tuple[AuditEvent, ...]:
        return tuple(e.event for e in self._entries)

    def for_customer(self, customer_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e.event for e in self._entries if e.event.customer_id == customer_id)

    def for_consent(self, consent_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e.event for e in self._entries if e.event.consent_id == consent_id)

    def __len__(self) -> int:
        return len(self._entries)
