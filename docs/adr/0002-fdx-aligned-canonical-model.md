# ADR 0002 — An FDX-aligned canonical model

**Status:** Accepted (Item 2)

## Context

Data arrives from many sources in many shapes (a clean FDX bank, a messy legacy
system, a scraped HTML statement). Everything downstream — the consent gate, the
dashboards, the agent — needs *one* shape to reason about. The design of that
shape sets the ceiling for the whole system's correctness.

## Decision

Define a **canonical model modelled on the FDX data model** (`Account`,
`Balance`, `Transaction`, `InvestmentHolding`, `Customer`, `Consent`) with these
rules baked in:

- **Money is `Decimal`, never `float`.** Binary floats can't represent values
  like `0.10` exactly; for financial data that's a correctness bug, not a
  rounding nicety.
- **Timestamps are timezone-aware.** Naive datetimes are rejected — an audit log
  that can't pin an event to an absolute instant is worthless.
- **camelCase on the wire, snake_case in code.** FDX/JSON is camelCase; the code
  stays Pythonic. Serialization bridges the two; input accepts either.
- **`extra="forbid"`.** The canonical model is the contract; an unexpected field
  is almost always a normalizer bug, so surface it loudly.
- **Controlled vocabularies as enums**, with cross-field validators (e.g. an
  account's type must belong to its category; a POSTED transaction needs a posted
  timestamp).

## Alternatives

- **Pass source dicts around untyped** — fastest to start, but pushes every
  quirk and rounding risk into every consumer. Rejected.
- **Adopt the full FDX spec verbatim** — far larger than this project needs;
  we take a faithful, pragmatic subset.

## Consequences

- Adapters have a precise target; schema drift is caught at the boundary.
- The consent layer gates and minimizes a *known* set of fields (ADR 0003–0004).
- The model is FDX-*aligned*, not FDX-*complete* — a deliberate scope choice.
