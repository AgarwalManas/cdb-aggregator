# ADR 0003 — Consent as a gate every read passes

**Status:** Accepted (Item 7)

## Context

Consent is the feature that separates an accredited open-banking participant from
a credential-storing screen scraper. If consent is enforced by ad-hoc `if` checks
sprinkled through the codebase, it *will* eventually be forgotten on some path —
and the one forgotten path is the breach.

## Decision

Make consent a **single choke point** that every data read passes through:

- `Consent` is a first-class, behavioral model — granular **scopes**, an
  **expiry**, and **revocation** — that answers questions (`is_active`,
  `permits`, `covers_account`) with one tested definition.
- A **`ConsentGate`** evaluates each read and returns a structured
  `ConsentDecision` with a specific denial reason (`NO_CONSENT`, `INACTIVE`,
  `SCOPE_NOT_GRANTED`, `ACCOUNT_NOT_COVERED`).
- A **`ConsentEnforcingReader`** wraps any source adapter and is the *only* way
  application code reads data. Each read maps to the scope it requires; there is
  no un-gated path to the adapters.

Downstream code (dashboards, agent) depends on the reader, never on adapters
directly.

## Alternatives

- **Middleware/decorator per endpoint** — better than scattered checks, but still
  leaves the door open to a new endpoint that forgets the decorator. The reader
  makes the *data access itself* the gated operation, which is harder to bypass.
- **Scattered inline checks** — rejected for the reason above.

## Consequences

- "No active, in-scope grant" provably means "no data".
- Distinct denial reasons make refusals explainable (Transparency).
- The gate is the natural place to hang the audit log and minimization
  (ADR 0004) and to enforce agent delegation (ADR 0005).
