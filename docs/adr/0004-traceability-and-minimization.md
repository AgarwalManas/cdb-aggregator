# ADR 0004 — Append-only audit log + field-level minimization

**Status:** Accepted (Item 8)

## Context

FDX's principles include **Traceability** ("who accessed what, when, under which
grant?") and **Control** (share only what's needed). Being *allowed* to read the
customer record shouldn't mean every field comes back, and every access — allowed
or denied — should leave a record.

## Decision

Two enforcement points, both hung off the enforcing reader (ADR 0003):

- **Append-only audit log.** Every read is recorded as an immutable `AuditEvent`
  tied to the grant it relied on, capturing the action, scope, account, decision
  + reason, how many records were disclosed, and which field clusters were
  withheld. The only mutation is `record()`; reads return copies. (A real
  deployment writes this to durable, tamper-evident storage.)
- **Field-level data minimization.** A read returns only the fields the granted
  scopes permit: contact details are withheld without `CUSTOMER_CONTACT`; balance
  amounts are withheld from an account without `BALANCES`. Minimizers return a
  redacted *copy* plus the names of withheld clusters, so the audit log can record
  what was minimized away as well as what was disclosed.

## Alternatives

- **Log only successful reads** — rejected; a *blocked* access is exactly the
  kind of event a trail should capture.
- **All-or-nothing per scope** — coarser than needed. Minimizing within a granted
  scope is what makes "share only what's needed" real.

## Consequences

- Consent decisions are auditable end to end; the dashboard shows the trail.
- The same trail attributes agent access to the agent identity (ADR 0005).
- Minimization affects downstream aggregation honestly — a balance you didn't
  share drops out of net worth, surfaced as *excluded*, not silently dropped.
