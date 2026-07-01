# Build Roadmap

How this project was built: an FDX-first Consumer-Driven Banking aggregator whose
core is a **consent + traceability layer**, assembled in dependency order. Each item
below landed as a commit tagged `item-NN`, so the history reads as a navigable
timeline (`git checkout item-07` to see the consent layer in isolation, for example).
See [`research-report.md`](research-report.md) for the regulatory and standards context.

## Phase 0 — Foundation
- **Item 1 — Repo scaffold.** Runnable skeleton (FastAPI backend, `frontend/`
  placeholder), config, health check, and a README framed around Consumer-Driven
  Banking + FDX.
- **Item 2 — Canonical data model.** The FDX-aligned domain types — `Account`,
  `Balance`, `Transaction`, `InvestmentHolding`, `Customer`, `Consent` — with
  validation and unit tests. Everything downstream normalizes into this.

## Phase 1 — Data ingestion & normalization
- **Item 3 — Mock FDX data provider.** A standalone mock bank returning FDX-shaped
  JSON behind a mock OAuth2 token flow: the clean, standards-native source.
- **Item 4 — Second source (messy schema).** A second mock source whose schema
  deliberately differs from FDX, so the normalizer has something hard to map.
- **Item 5 — Normalizer / adapter layer.** One adapter per source mapping raw data
  into the canonical model behind a common interface, with per-adapter tests.
- **Item 6 — Screen-scraping contrast.** A fragile HTML-statement source parsed by a
  scraper adapter, plus a comparison contrasting credential-based scraping with
  token-based FDX access.

## Phase 2 — Consent & traceability (the core)
- **Item 7 — Consent model + enforcement.** The consent lifecycle (granular scopes,
  expiry, grant/revoke) and middleware so every data read is gated on an active,
  in-scope grant. Tests cover the enforcement path.
- **Item 8 — Traceability audit log + data minimization.** An append-only access log
  tied to each grant, plus field-level minimization so a read returns only what the
  granted scopes permit.
- **Item 9 — Consent dashboard (React).** The UI for the consent layer: connections,
  scopes, expiry, one-tap revoke, and a view of the audit log.

## Phase 3 — Aggregation UX
- **Item 10 — Unified accounts + net-worth dashboard (React).** Merged accounts,
  merged transaction feed, and a household net-worth view — all reads flowing through
  the consent gate.

## Phase 4 — Differentiator
- **Item 11 — Agentic delegation.** A scoped, revocable, fully-logged task delegated
  to an AI agent (e.g. surfacing idle cash), modeled as a consent to an agent
  identity: suggestion-only, and governed like any other data access.

## Phase 5 — Packaging
- **Item 12 — Test hardening + CI.** Broadened coverage across adapters, consent
  enforcement, and minimization, plus a GitHub Actions workflow running lint, tests,
  and the frontend build.
- **Item 13 — README, ADRs, and the screen-scraping writeup.** A README framed around
  the regulatory moment and the consent architecture, a set of architecture decision
  records, and a standalone explainer on why screen-scraping is being replaced.
- **Item 14 — Project walkthrough.** A concise walkthrough of the problem,
  architecture, the consent layer, and the trade-offs chosen.

## Dependency order
1 → 2 → (3, 4) → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14

## Follow-on work
Subsequent UI refinement and technical hardening (design system, dark mode, richer
audit-log controls, a tamper-evident hash-chained log, FAPI/FDX conformance, and
more) are tracked in [`polish-todo.md`](polish-todo.md), continuing the same
`item-NN` tag convention.

## Principles carried throughout
- **Keep it simple; make it obvious.** Small, typed, well-named modules; structure
  mirrors the data flow.
- **Consent is the gate, not a feature.** Reads are impossible without an active,
  in-scope grant, and traceable when they happen.
- **Real tests from the start**, growing with each phase.
- **FDX-first, honest about scope** — built to the standard, without claiming
  certification that doesn't exist yet.
