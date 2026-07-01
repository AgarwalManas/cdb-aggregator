"""Consent storage and lifecycle: grant, look up, revoke.

An in-memory store keyed by consent id. It's the source of truth the enforcement
gate reads and the lifecycle operations (grant/revoke) write. Kept deliberately
simple — a real deployment swaps this for a database, but the interface (and the
immutability of a revoked grant) is what matters.

Time is passed in explicitly (``now=``) rather than read from the clock inside,
so the lifecycle is deterministic and testable; it defaults to "now" for callers
that don't care.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from app.models import Consent, ConsentScope, ConsentStatus


class ConsentStore:
    """Holds consent grants and their lifecycle transitions."""

    def __init__(self) -> None:
        self._by_id: dict[str, Consent] = {}

    # --- reads ---------------------------------------------------------------

    def get(self, consent_id: str) -> Consent | None:
        return self._by_id.get(consent_id)

    def all(self) -> list[Consent]:
        return list(self._by_id.values())

    def for_customer(self, customer_id: str) -> list[Consent]:
        return [c for c in self._by_id.values() if c.customer_id == customer_id]

    def for_customer_recipient(self, customer_id: str, recipient: str) -> list[Consent]:
        """All grants from ``customer_id`` to ``recipient`` (any status).

        The gate filters these by activity/scope; returning every status here
        keeps the store dumb and the policy in one place.
        """
        return [
            c
            for c in self._by_id.values()
            if c.customer_id == customer_id and c.recipient == recipient
        ]

    # --- lifecycle -----------------------------------------------------------

    def add(self, consent: Consent) -> Consent:
        """Insert or replace a grant (revocation replaces by the same id)."""
        self._by_id[consent.consent_id] = consent
        return consent

    def grant(
        self,
        customer_id: str,
        recipient: str,
        scopes: Iterable[ConsentScope],
        *,
        duration: timedelta,
        account_ids: Iterable[str] | None = None,
        now: datetime | None = None,
        consent_id: str | None = None,
    ) -> Consent:
        """Create and store an active grant valid for ``duration``."""
        created = now or datetime.now(UTC)
        consent = Consent(
            consent_id=consent_id or f"consent-{secrets.token_hex(8)}",
            customer_id=customer_id,
            recipient=recipient,
            scopes=set(scopes),
            status=ConsentStatus.GRANTED,
            created_at=created,
            expires_at=created + duration,
            account_ids=list(account_ids or []),
        )
        return self.add(consent)

    def revoke(self, consent_id: str, *, now: datetime | None = None) -> Consent:
        """Revoke a stored grant, replacing it with its revoked version.

        Raises ``KeyError`` if the grant is unknown.
        """
        consent = self._by_id[consent_id]
        return self.add(consent.revoke(now or datetime.now(UTC)))
