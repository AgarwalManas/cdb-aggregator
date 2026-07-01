"""The consent-gated alias resolver — route on a lookup, not on the identifier.

Resolving an alias never returns the raw institution / transit / account. It
returns a **one-time routing token**, so a counterparty learns *where to send
money* without ever learning the user's bank or branch. Resolution is gated on an
active, in-scope consent covering the target account, and *every* resolution —
allowed or denied — is written to the traceability trail, attributed to whoever
asked. Redeeming a token (the settlement step, out of band) reveals the
coordinates exactly once.

Re-pointing the alias to a different source is itself a scoped, logged event —
portability expressed as a consent action.

Scope note: this demonstrates the addressing/portability *pattern* on mock data.
It moves no money, is not a central registry, and settles over no payment rail —
the same honest-scope line the rest of the project draws.
"""

from __future__ import annotations

import secrets
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.consent import AuditEvent, AuditLog, ConsentGate, SqliteAuditLog
from app.models import ConsentScope

from .registry import Alias, AliasRegistry

#: Resolving an address discloses routing coordinates derived from account details.
ROUTING_SCOPE = ConsentScope.ACCOUNT_DETAILS
#: A routing token is short-lived and single-use.
TOKEN_TTL = timedelta(minutes=5)

#: Clearly-synthetic institution numbers for the demo sources — never real.
_INSTITUTIONS = {
    "Mock FDX Bank": "001",
    "Legacy Bank": "002",
    "OldBank (scraped)": "003",
}


@dataclass(frozen=True)
class RoutingCoordinates:
    """Deterministic, obviously-synthetic coordinates for the demo — never real."""

    institution: str
    transit: str
    masked_account: str
    source_label: str


def coordinates_for(account_id: str, source_label: str) -> RoutingCoordinates:
    """Stable fake coordinates derived from the account id (no randomness)."""
    digest = zlib.crc32(account_id.encode())
    return RoutingCoordinates(
        institution=_INSTITUTIONS.get(source_label, "000"),
        transit=f"{digest % 100000:05d}",
        masked_account=f"···· {digest % 10000:04d}",
        source_label=source_label,
    )


@dataclass
class _IssuedToken:
    account_id: str
    source_label: str
    issued_at: datetime
    used: bool = False


@dataclass(frozen=True)
class Resolution:
    """The answer a counterparty gets: a token, or a reason it got nothing."""

    allowed: bool
    handle: str
    routing_token: str | None
    disclosed: str  # "one-time routing token" | "nothing"
    reason: str | None


class AliasResolver:
    """Resolves an alias to a one-time routing token — consent-gated and logged."""

    def __init__(
        self,
        registry: AliasRegistry,
        gate: ConsentGate,
        audit: AuditLog | SqliteAuditLog,
        *,
        customer_id: str,
        recipient: str,
        source_label: Callable[[str], str | None],
    ) -> None:
        self._registry = registry
        self._gate = gate
        self._audit = audit
        self._customer_id = customer_id
        self._recipient = recipient
        self._source_label = source_label
        self._tokens: dict[str, _IssuedToken] = {}

    def resolve(self, handle: str, *, requester: str, at: datetime | None = None) -> Resolution:
        now = at or datetime.now(UTC)
        alias = self._registry.get(handle)
        if alias is None:
            return Resolution(False, handle, None, "nothing", "unknown alias")

        decision = self._gate.check(
            self._customer_id, self._recipient, ROUTING_SCOPE, account_id=alias.account_id, at=now
        )
        # Every resolution — allowed or denied — lands in the traceability trail,
        # attributed to whoever asked.
        self._audit.record(
            AuditEvent(
                occurred_at=now,
                action="resolve_alias",
                customer_id=self._customer_id,
                recipient=requester,
                scope=ROUTING_SCOPE,
                allowed=decision.allowed,
                account_id=alias.account_id,
                reason=decision.reason,
                consent_id=decision.consent.consent_id if decision.consent else None,
                record_count=1 if decision.allowed else 0,
                withheld=(),
            )
        )
        if not decision.allowed:
            reason = decision.reason.value if decision.reason else None
            return Resolution(False, handle, None, "nothing", reason)

        token = secrets.token_urlsafe(16)
        self._tokens[token] = _IssuedToken(
            account_id=alias.account_id,
            source_label=self._source_label(alias.account_id) or "unknown",
            issued_at=now,
        )
        return Resolution(True, handle, token, "one-time routing token", None)

    def exchange(self, token: str, *, at: datetime | None = None) -> RoutingCoordinates | None:
        """Redeem a routing token for coordinates — once, and before it expires."""
        now = at or datetime.now(UTC)
        issued = self._tokens.get(token)
        if issued is None or issued.used or now - issued.issued_at > TOKEN_TTL:
            return None
        issued.used = True
        return coordinates_for(issued.account_id, issued.source_label)

    def repoint(self, handle: str, account_id: str, *, at: datetime | None = None) -> Alias | None:
        """Re-point the alias — but only to an account the user actually shares.

        Returns ``None`` if the handle is unknown or the new target isn't covered
        by an active grant; the change is a scoped, logged consent event otherwise.
        """
        now = at or datetime.now(UTC)
        if self._registry.get(handle) is None:
            return None
        decision = self._gate.check(
            self._customer_id, self._recipient, ROUTING_SCOPE, account_id=account_id, at=now
        )
        if not decision.allowed:
            return None
        alias = self._registry.repoint(handle, account_id, at=now)
        self._audit.record(
            AuditEvent(
                occurred_at=now,
                action="repoint_alias",
                customer_id=self._customer_id,
                recipient=self._recipient,
                scope=ROUTING_SCOPE,
                allowed=True,
                account_id=account_id,
                reason=None,
                consent_id=decision.consent.consent_id if decision.consent else None,
                record_count=1,
                withheld=(),
            )
        )
        return alias

    def resolutions(self) -> list[AuditEvent]:
        """The resolution history — the alias slice of the traceability trail."""
        return [e for e in self._audit.all() if e.action == "resolve_alias"]
