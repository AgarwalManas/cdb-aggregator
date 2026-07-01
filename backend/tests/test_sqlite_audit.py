"""Tests for the audit-log store seam (item-25).

The audit log has two interchangeable backends — in-memory and SQLite — behind
one interface. These run the same invariants against both (so the seam is real),
prove the SQLite log survives a reopen (durability is the point), and cover the
config-driven factory.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.consent import (
    GENESIS_HASH,
    AuditEvent,
    AuditLog,
    DenialReason,
    SqliteAuditLog,
    create_audit_log,
)
from app.core.config import Settings
from app.models import ConsentScope

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _event(
    i: int,
    *,
    customer: str = "cust",
    consent: str = "grant",
    allowed: bool = True,
    reason: DenialReason | None = None,
    withheld: tuple[str, ...] = (),
) -> AuditEvent:
    return AuditEvent(
        occurred_at=BASE + timedelta(minutes=i),
        action=f"read_{i}",
        customer_id=customer,
        recipient="aggregator",
        scope=ConsentScope.BALANCES,
        allowed=allowed,
        account_id="acc-1",
        reason=reason,
        consent_id=consent,
        record_count=1 if allowed else 0,
        withheld=withheld,
    )


@pytest.fixture(params=["memory", "sqlite"])
def audit_log(request, tmp_path):
    if request.param == "memory":
        log = AuditLog()
    else:
        log = SqliteAuditLog(str(tmp_path / "audit.sqlite3"))
    yield log
    close = getattr(log, "close", None)
    if close:
        close()


# --- Same behavior across both backends --------------------------------------


def test_head_is_genesis_when_empty(audit_log) -> None:
    assert audit_log.head() == GENESIS_HASH
    assert len(audit_log) == 0


def test_records_chain_and_verify(audit_log) -> None:
    for i in range(3):
        audit_log.record(_event(i))

    assert len(audit_log) == 3
    assert [e.action for e in audit_log.all()] == ["read_0", "read_1", "read_2"]

    entries = audit_log.chain()
    assert entries[0].prev_hash == GENESIS_HASH
    assert entries[1].prev_hash == entries[0].entry_hash
    assert audit_log.head() == entries[-1].entry_hash

    result = audit_log.verify()
    assert result.valid is True
    assert result.checked == 3
    assert result.broken_at is None


def test_queries_by_customer_and_consent(audit_log) -> None:
    audit_log.record(_event(0, customer="c1", consent="grant-a"))
    audit_log.record(_event(1, customer="c2", consent="grant-b"))
    assert [e.customer_id for e in audit_log.for_customer("c1")] == ["c1"]
    assert [e.consent_id for e in audit_log.for_consent("grant-b")] == ["grant-b"]


def test_preserves_denied_events(audit_log) -> None:
    audit_log.record(_event(0, allowed=False, reason=DenialReason.NO_CONSENT))
    (event,) = audit_log.all()
    assert event.allowed is False
    assert event.reason is DenialReason.NO_CONSENT
    assert event.record_count == 0


# --- SQLite durability + factory ---------------------------------------------


def test_sqlite_persists_across_reopen(tmp_path) -> None:
    path = str(tmp_path / "audit.sqlite3")
    log = SqliteAuditLog(path)
    log.record(_event(0))
    log.record(
        _event(1, allowed=False, reason=DenialReason.SCOPE_NOT_GRANTED, withheld=("balances",))
    )
    log.close()

    reopened = SqliteAuditLog(path)
    assert len(reopened) == 2
    assert reopened.verify().valid is True  # the chain survives intact
    events = reopened.all()
    assert events[1].reason is DenialReason.SCOPE_NOT_GRANTED
    assert events[1].withheld == ("balances",)  # round-trips through JSON
    reopened.close()


def test_factory_selects_backend_from_config(tmp_path) -> None:
    memory = create_audit_log(Settings(audit_backend="memory"))
    assert isinstance(memory, AuditLog)

    sqlite = create_audit_log(
        Settings(audit_backend="sqlite", sqlite_path=str(tmp_path / "factory.sqlite3"))
    )
    assert isinstance(sqlite, SqliteAuditLog)
    sqlite.close()
