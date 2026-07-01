"""The consent gate — the check every data read must pass.

Given a customer, the recipient asking, a required scope, and (optionally) an
account, the gate decides whether an *active, in-scope, account-covering* grant
exists. It returns a structured :class:`ConsentDecision` (which Item 8's audit
log will record verbatim) and offers :meth:`ConsentGate.authorize`, which raises
:class:`ConsentDenied` for call sites that just want allow-or-fail.

The denial reasons are distinct on purpose — "you never consented" is a
different conversation from "your consent expired" or "that scope wasn't
granted" — and they map cleanly onto the transparency the whole project argues
for.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.models import Consent, ConsentScope

from .store import ConsentStore


class DenialReason(StrEnum):
    """Why a consent check failed. Ordered from most to least fundamental."""

    NO_CONSENT = "NO_CONSENT"  # the customer never granted this recipient anything
    INACTIVE = "INACTIVE"  # a grant exists but is expired / revoked / not yet active
    SCOPE_NOT_GRANTED = "SCOPE_NOT_GRANTED"  # active, but this data cluster isn't covered
    ACCOUNT_NOT_COVERED = "ACCOUNT_NOT_COVERED"  # in scope, but not for this account


@dataclass(frozen=True)
class ConsentDecision:
    """The outcome of a gate check — allow or deny, with the reason and grant."""

    allowed: bool
    scope: ConsentScope
    account_id: str | None = None
    reason: DenialReason | None = None
    consent: Consent | None = None


class ConsentDenied(Exception):
    """Raised by :meth:`ConsentGate.authorize` when a read isn't permitted."""

    def __init__(self, decision: ConsentDecision) -> None:
        self.decision = decision
        target = f" for account {decision.account_id!r}" if decision.account_id else ""
        super().__init__(f"consent denied ({decision.reason}) for {decision.scope}{target}")


class ConsentGate:
    """Enforces consent for reads against a :class:`ConsentStore`."""

    def __init__(self, store: ConsentStore) -> None:
        self._store = store

    def check(
        self,
        customer_id: str,
        recipient: str,
        scope: ConsentScope,
        *,
        account_id: str | None = None,
        at: datetime | None = None,
    ) -> ConsentDecision:
        """Evaluate a read without raising. Returns the decision (for logging)."""

        def deny(reason: DenialReason) -> ConsentDecision:
            return ConsentDecision(False, scope, account_id, reason=reason)

        candidates = self._store.for_customer_recipient(customer_id, recipient)
        if not candidates:
            return deny(DenialReason.NO_CONSENT)

        active = [c for c in candidates if c.is_active(at)]
        if not active:
            return deny(DenialReason.INACTIVE)

        scoped = [c for c in active if scope in c.scopes]
        if not scoped:
            return deny(DenialReason.SCOPE_NOT_GRANTED)

        if account_id is not None:
            covering = [c for c in scoped if c.covers_account(account_id)]
            if not covering:
                return deny(DenialReason.ACCOUNT_NOT_COVERED)
            return ConsentDecision(True, scope, account_id, consent=covering[0])

        return ConsentDecision(True, scope, account_id, consent=scoped[0])

    def authorize(
        self,
        customer_id: str,
        recipient: str,
        scope: ConsentScope,
        *,
        account_id: str | None = None,
        at: datetime | None = None,
    ) -> Consent:
        """Like :meth:`check`, but raise :class:`ConsentDenied` unless allowed."""
        decision = self.check(customer_id, recipient, scope, account_id=account_id, at=at)
        if not decision.allowed or decision.consent is None:
            raise ConsentDenied(decision)
        return decision.consent
