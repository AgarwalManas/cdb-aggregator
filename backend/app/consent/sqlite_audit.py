"""SQLite-backed audit log — a durable implementation of the same interface.

The traceability log's whole value is that it *persists* and can't be quietly
altered, so it's the first store to get a real backend behind the in-memory seam
(item-25). ``SqliteAuditLog`` speaks the same methods as
:class:`app.consent.audit.AuditLog` (``record`` / ``all`` / ``head`` / ``chain`` /
``verify`` / ``for_customer`` / ``for_consent`` / ``len``), so the reader and the
API can't tell which one they hold.

Selection is by config and defaults to in-memory — see :func:`create_audit_log`.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING

from app.models import ConsentScope

from .audit import (
    GENESIS_HASH,
    AuditEvent,
    AuditLog,
    ChainedEntry,
    ChainVerification,
    hash_event,
    verify_chain,
)
from .enforcement import DenialReason

if TYPE_CHECKING:
    from app.core.config import Settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at  TEXT NOT NULL,
    action       TEXT NOT NULL,
    customer_id  TEXT NOT NULL,
    recipient    TEXT NOT NULL,
    scope        TEXT NOT NULL,
    allowed      INTEGER NOT NULL,
    account_id   TEXT,
    reason       TEXT,
    consent_id   TEXT,
    record_count INTEGER NOT NULL,
    withheld     TEXT NOT NULL,
    prev_hash    TEXT NOT NULL,
    entry_hash   TEXT NOT NULL
)
"""


class SqliteAuditLog:
    """Append-only, hash-chained audit log persisted in SQLite."""

    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- write ---------------------------------------------------------------

    def record(self, event: AuditEvent) -> AuditEvent:
        prev_hash = self.head()
        entry_hash = hash_event(event, prev_hash)
        self._conn.execute(
            """
            INSERT INTO audit (
                occurred_at, action, customer_id, recipient, scope, allowed,
                account_id, reason, consent_id, record_count, withheld,
                prev_hash, entry_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.occurred_at.isoformat(),
                event.action,
                event.customer_id,
                event.recipient,
                event.scope.value,
                1 if event.allowed else 0,
                event.account_id,
                event.reason.value if event.reason else None,
                event.consent_id,
                event.record_count,
                json.dumps(list(event.withheld)),
                prev_hash,
                entry_hash,
            ),
        )
        self._conn.commit()
        return event

    # --- read ----------------------------------------------------------------

    def head(self) -> str:
        row = self._conn.execute(
            "SELECT entry_hash FROM audit ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else GENESIS_HASH

    def _entries(self) -> list[ChainedEntry]:
        rows = self._conn.execute(
            """
            SELECT occurred_at, action, customer_id, recipient, scope, allowed,
                   account_id, reason, consent_id, record_count, withheld,
                   prev_hash, entry_hash
            FROM audit ORDER BY seq ASC
            """
        ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def chain(self) -> tuple[ChainedEntry, ...]:
        return tuple(self._entries())

    def all(self) -> tuple[AuditEvent, ...]:
        return tuple(e.event for e in self._entries())

    def for_customer(self, customer_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e.event for e in self._entries() if e.event.customer_id == customer_id)

    def for_consent(self, consent_id: str) -> tuple[AuditEvent, ...]:
        return tuple(e.event for e in self._entries() if e.event.consent_id == consent_id)

    def verify(self) -> ChainVerification:
        return verify_chain(self._entries())

    def __len__(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]


def _row_to_entry(row: tuple) -> ChainedEntry:
    (
        occurred_at,
        action,
        customer_id,
        recipient,
        scope,
        allowed,
        account_id,
        reason,
        consent_id,
        record_count,
        withheld,
        prev_hash,
        entry_hash,
    ) = row
    event = AuditEvent(
        occurred_at=datetime.fromisoformat(occurred_at),
        action=action,
        customer_id=customer_id,
        recipient=recipient,
        scope=ConsentScope(scope),
        allowed=bool(allowed),
        account_id=account_id,
        reason=DenialReason(reason) if reason is not None else None,
        consent_id=consent_id,
        record_count=record_count,
        withheld=tuple(json.loads(withheld)),
    )
    return ChainedEntry(event=event, prev_hash=prev_hash, entry_hash=entry_hash)


def create_audit_log(settings: Settings) -> AuditLog | SqliteAuditLog:
    """Pick the audit backend from config: ``sqlite`` for durability, else memory."""
    if settings.audit_backend == "sqlite":
        return SqliteAuditLog(settings.sqlite_path)
    return AuditLog()
