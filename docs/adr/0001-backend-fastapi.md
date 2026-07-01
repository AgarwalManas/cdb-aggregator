# ADR 0001 — Backend framework: FastAPI (Python)

**Status:** Accepted (Item 1)

## Context

The project needs a backend for the aggregator API, the mock FDX/legacy/scraped
providers, and the consent engine. The candidates considered were Ruby on Rails,
Python (FastAPI), and Node/Express.

Selection criteria: fit for the data-normalization and consent work, speed of
building a legible portfolio codebase, and strong typing/validation for a
financial data model where correctness matters.

## Decision

Use **Python 3.11 + FastAPI**, with **Pydantic v2** for the domain model and
validation and **pydantic-settings** for typed configuration.

- Pydantic v2 gives a validated, typed canonical model almost for free — exactly
  what the FDX-shaped data layer needs (see ADR 0002).
- FastAPI's dependency-injection and app-factory pattern make the consent gate a
  natural, testable choke point.
- Python keeps the normalizer/adapter code (the heart of the ingestion work)
  short and readable.

The frontend is **React** regardless of backend choice.

## Alternatives

- **Rails** — strong "drop into a Rails shop" signal, but heavier for the
  schema-normalization and typed-model work at the centre of this build.
- **Node/Express** — one language across the stack, but weaker out-of-the-box
  typed validation than Pydantic v2 for the domain model.

## Consequences

- A single, typed source of truth for money and dates (ADR 0002).
- FastAPI's OpenAPI docs come for free (`/docs`).
- Two languages in the repo (Python backend, JS frontend) — an accepted cost for
  using the right tool on each side.
