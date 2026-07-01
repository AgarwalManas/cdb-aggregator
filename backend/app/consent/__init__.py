"""Consent + traceability layer — the star of this project.

- **Item 7 (this):** the consent lifecycle (grant/revoke over the ``Consent``
  model's granular scopes and expiry) and enforcement so every data read is
  gated on an active, in-scope grant.
  - :class:`ConsentStore` — grant, look up, revoke.
  - :class:`ConsentGate` — the check every read passes (:class:`ConsentDecision`
    / :class:`ConsentDenied`, with distinct :class:`DenialReason` values).
  - :class:`ConsentEnforcingReader` — wraps an adapter so nothing is returned
    without clearing the gate.
- **Item 8 (next):** an append-only traceability audit log tied to each grant,
  plus field-level data minimization per scope.

Maps to FDX's five principles: Control, Access, Transparency, Traceability, Security.
"""

from __future__ import annotations

from .enforcement import (
    ConsentDecision,
    ConsentDenied,
    ConsentGate,
    DenialReason,
)
from .reader import ConsentEnforcingReader
from .store import ConsentStore

__all__ = [
    "ConsentStore",
    "ConsentGate",
    "ConsentDecision",
    "ConsentDenied",
    "DenialReason",
    "ConsentEnforcingReader",
]
