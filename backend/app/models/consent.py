"""Consent — the grant that authorizes data access.

This is the canonical shape of the project's star feature. It is intentionally
behavioral, not just a data bag: the enforcement middleware in Item 7 and the
audit log in Item 8 ask a ``Consent`` questions — *are you active right now? do
you permit the BALANCES scope? do you cover this account?* — so those questions
live here as methods with a single, tested definition.

Modeled on FDX's consent concept (granular data clusters, a defined lifecycle,
time-limited grants, explicit revocation). Scopes map one-to-one onto the
canonical data clusters a read can touch, which is what makes field/cluster-level
data minimization (Item 8) tractable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import AwareDatetime, model_validator

from .common import EntityId, FdxBaseModel


class ConsentScope(StrEnum):
    """A data cluster a consent grant can authorize.

    Each value corresponds to a slice of the canonical model. Enforcement (Item
    7) checks the relevant scope before returning data; minimization (Item 8)
    uses the granted set to decide which fields may leave the system.
    """

    ACCOUNT_DETAILS = "ACCOUNT_DETAILS"
    BALANCES = "BALANCES"
    TRANSACTIONS = "TRANSACTIONS"
    INVESTMENT_HOLDINGS = "INVESTMENT_HOLDINGS"
    CUSTOMER_CONTACT = "CUSTOMER_CONTACT"
    CUSTOMER_IDENTITY = "CUSTOMER_IDENTITY"


class ConsentStatus(StrEnum):
    """Lifecycle state of a consent grant.

    ``EXPIRED`` is computed from the clock rather than stored — see
    :meth:`Consent.effective_status`. The stored ``status`` only needs to capture
    the parts the clock can't: not-yet-active, active, or explicitly revoked.
    """

    PENDING = "PENDING"
    GRANTED = "GRANTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class Consent(FdxBaseModel):
    """A time-limited, revocable, scoped authorization to access a customer's data."""

    consent_id: EntityId
    #: The customer who granted (or is being asked for) consent.
    customer_id: EntityId
    #: The party the data is being shared with (this aggregator, or a downstream
    #: recipient in a delegation scenario).
    recipient: EntityId

    #: The data clusters authorized. Must be non-empty — a consent that permits
    #: nothing is not a consent.
    scopes: set[ConsentScope]
    status: ConsentStatus = ConsentStatus.GRANTED

    created_at: AwareDatetime
    expires_at: AwareDatetime
    revoked_at: AwareDatetime | None = None

    #: Accounts this grant is scoped to. Empty means "all of the customer's
    #: accounts" — the common case for a full-aggregation consent.
    account_ids: list[EntityId] = []

    # --- Validators ---------------------------------------------------------

    @model_validator(mode="after")
    def _scopes_non_empty(self) -> Consent:
        if not self.scopes:
            raise ValueError("a consent must grant at least one scope")
        return self

    @model_validator(mode="after")
    def _expiry_after_creation(self) -> Consent:
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        return self

    @model_validator(mode="after")
    def _revocation_consistent(self) -> Consent:
        """``status == REVOKED`` and ``revoked_at`` must agree.

        Each implies the other: a revoked grant records when, and a recorded
        revocation time means the grant is revoked. Catches half-applied state.
        """

        is_revoked = self.status is ConsentStatus.REVOKED
        has_time = self.revoked_at is not None
        if is_revoked and not has_time:
            raise ValueError("a REVOKED consent requires a revoked_at timestamp")
        if has_time and not is_revoked:
            raise ValueError("revoked_at is set but status is not REVOKED")
        return self

    # --- Behavior (the questions enforcement will ask) ----------------------

    @staticmethod
    def _resolve(at: datetime | None) -> datetime:
        return at if at is not None else datetime.now(UTC)

    def effective_status(self, at: datetime | None = None) -> ConsentStatus:
        """The status accounting for the clock.

        Returns ``EXPIRED`` once past ``expires_at`` (unless already revoked);
        otherwise the stored status. This is what callers should display and
        gate on, rather than the raw ``status`` field.
        """

        now = self._resolve(at)
        if self.status is ConsentStatus.REVOKED:
            return ConsentStatus.REVOKED
        if now >= self.expires_at:
            return ConsentStatus.EXPIRED
        return self.status

    def is_active(self, at: datetime | None = None) -> bool:
        """True iff the grant authorizes access *right now*.

        Active means: granted (not pending/revoked), already started, and not yet
        expired. This single predicate is the gate every read passes through.
        """

        now = self._resolve(at)
        return self.effective_status(now) is ConsentStatus.GRANTED and self.created_at <= now

    def permits(self, scope: ConsentScope, at: datetime | None = None) -> bool:
        """True iff the grant is active and includes ``scope``."""
        return self.is_active(at) and scope in self.scopes

    def covers_account(self, account_id: str) -> bool:
        """Whether this grant applies to ``account_id``.

        An empty ``account_ids`` means the grant covers all of the customer's
        accounts; otherwise the account must be explicitly listed.
        """

        return not self.account_ids or account_id in self.account_ids

    def revoke(self, at: datetime | None = None) -> Consent:
        """Return a revoked copy of this grant.

        Returns a new instance (the original is left untouched) so callers can
        keep an immutable history of consent states — useful for the audit log.
        Re-validated on construction, so the result is guaranteed consistent.
        """

        when = self._resolve(at)
        return self.model_validate(
            {**self.model_dump(), "status": ConsentStatus.REVOKED, "revoked_at": when}
        )
