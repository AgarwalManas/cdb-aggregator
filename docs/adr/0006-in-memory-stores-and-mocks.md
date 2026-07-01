# ADR 0006 — In-memory stores + mock providers (SQLite behind the seam)

**Status:** Accepted (Items 3–11); extended in item-25

## Context

The project demonstrates the *architecture* open banking calls for. It does not
(and, as of early 2026, cannot) integrate with a live financial institution or
regulator — Canada's Phase-1 read access had no firm Bank of Canada launch date.
So the sources and persistence are stand-ins.

## Decision

- **Mock providers, three of them**, standing in for real data sources: a clean
  FDX bank (OAuth2 + FDX JSON), a messy legacy bank (session auth + ad-hoc
  nested JSON), and a screen-scraped "OldBank" (login form + HTML statement). They
  describe the same underlying customer so the aggregator can merge them.
- **In-memory stores** for consent grants and the audit log, behind small
  interfaces (`ConsentStore`, `AuditLog`). Time is injected (`now=`) so lifecycle
  is deterministic and testable.
- A seeded **in-memory demo world** (`app.api.demo`) powers the dashboards with a
  realistic starting state, including a real audit trail.

### Update (item-25): a real backend behind the seam

To show the store interface is a genuine seam — not just a claim — the **audit
log now has a second, durable backend**: `SqliteAuditLog` implements the exact
same methods as the in-memory `AuditLog` (record / all / head / chain / verify /
for_customer / for_consent / len), persisting the hash chain in SQLite. The
backend is chosen by config (`CDB_AUDIT_BACKEND` = `memory` (default) | `sqlite`,
`CDB_SQLITE_PATH`), so the reader and the API can't tell which one they hold.

The audit log was picked first on purpose: its value *is* durability — a
tamper-evident trail you can't keep isn't much of a trail. `ConsentStore` can
follow the same pattern. Note the demo builds a fresh world per visitor session,
so pointing it at `sqlite` shares one file across sessions (fine for a durability
demo; the default `memory` keeps per-visitor isolation).

## Alternatives

- **Stand up Postgres + real OAuth against a sandbox bank** — more "production
  shaped", but adds infrastructure and an external dependency without changing the
  architecture being demonstrated. Deferred.

## Consequences

- The repo runs offline with `pip install` + `npm install`; CI needs no services.
- The store interfaces are the seam where a database drops in — demonstrated for
  the audit log (SQLite), with nothing above it changing.
- The build is honest about scope: it models the standard, it doesn't claim
  certified connectivity.
