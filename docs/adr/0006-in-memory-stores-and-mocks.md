# ADR 0006 — In-memory stores + mock providers (no database yet)

**Status:** Accepted (Items 3–11)

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

## Alternatives

- **Stand up Postgres + real OAuth against a sandbox bank** — more "production
  shaped", but adds infrastructure and an external dependency without changing the
  architecture being demonstrated. Deferred.

## Consequences

- The repo runs offline with `pip install` + `npm install`; CI needs no services.
- The store interfaces are the seam where a database drops in later; nothing above
  them changes.
- The build is honest about scope: it models the standard, it doesn't claim
  certified connectivity.
