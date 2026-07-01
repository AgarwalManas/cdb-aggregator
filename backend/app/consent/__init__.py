"""Consent + traceability layer — the star of this project.

- **Item 7:** the consent lifecycle (grant/revoke over the ``Consent`` model's
  granular scopes and expiry) and enforcement so every data read is gated on an
  active, in-scope grant.
  - :class:`ConsentStore` — grant, look up, revoke.
  - :class:`ConsentGate` — the check every read passes (:class:`ConsentDecision`
    / :class:`ConsentDenied`, with distinct :class:`DenialReason` values).
- **Item 8:** traceability + control.
  - :class:`AuditLog` / :class:`AuditEvent` — an append-only record of every
    access (allowed or denied), tied to the grant it relied on.
  - :func:`minimize_customer` / :func:`minimize_account` — field-level data
    minimization: return only what the granted scopes permit.
- :class:`ConsentEnforcingReader` wires all of it together: every read clears the
  gate, is logged, and comes back minimized.

Maps to FDX's five principles: Control, Access, Transparency, Traceability, Security.
"""

from __future__ import annotations

from .audit import AuditEvent, AuditLog
from .enforcement import (
    ConsentDecision,
    ConsentDenied,
    ConsentGate,
    DenialReason,
)
from .minimize import minimize_account, minimize_customer
from .reader import ConsentEnforcingReader
from .store import ConsentStore

__all__ = [
    "ConsentStore",
    "ConsentGate",
    "ConsentDecision",
    "ConsentDenied",
    "DenialReason",
    "ConsentEnforcingReader",
    "AuditLog",
    "AuditEvent",
    "minimize_customer",
    "minimize_account",
]
