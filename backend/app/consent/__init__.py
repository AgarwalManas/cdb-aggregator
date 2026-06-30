"""Consent + traceability layer — the star of this project.

Populated in **Items 7-8**:
- Item 7: the Consent lifecycle (granular scopes, expiry, grant/revoke) and
  enforcement middleware so every data read is gated on an active, in-scope grant.
- Item 8: an append-only traceability audit log tied to each grant, plus
  field-level data minimization per scope.

Maps to FDX's five principles: Control, Access, Transparency, Traceability, Security.
"""
