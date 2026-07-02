# Roadmap

`cdb-aggregator` was built as a sequence of small, self-contained **Items**, each
landing as one commit tagged `item-NN` so the history reads as a navigable
timeline — `git checkout item-07` to see the consent layer in isolation, `item-22`
for the hash chain, and so on. This file is the map: the **core build** (Items
1–14), the **follow-on** that refined and extended it (Items 15–33), and a later
**experience redesign** (Track 4) that reorganized the front end. All of it is
complete. For the regulatory and standards context, see
[`research-report.md`](research-report.md).

## Principles carried throughout

- **Consent is the gate, not a feature.** No read happens without an active,
  in-scope grant — and every read is traceable when it does.
- **Keep it simple; make it obvious.** Small, typed, well-named modules; structure
  mirrors the data flow.
- **Real tests from the start.** 100% backend coverage and warnings-as-errors,
  enforced in CI, growing with each item.
- **FDX-first, honest about scope.** Built to the standard; no claim of
  certification that doesn't exist yet. Forward-looking items that outrun the
  mock/in-memory stack are labelled **simulations**.
- **One item, one tagged commit** — each a reviewable step in a legible timeline.

---

## The core build (Items 1–14)

### Phase 0 — Foundation
- **Item 1 — Repo scaffold.** Runnable skeleton (FastAPI backend, `frontend/`
  placeholder), config, health check, README framed around Consumer-Driven
  Banking + FDX.
- **Item 2 — Canonical data model.** The FDX-aligned domain types — `Account`,
  `Balance`, `Transaction`, `InvestmentHolding`, `Customer`, `Consent` — with
  validation and tests. Everything downstream normalizes into this.

### Phase 1 — Data ingestion & normalization
- **Item 3 — Mock FDX data provider.** A standalone mock bank returning FDX-shaped
  JSON behind a mock OAuth2 flow: the clean, standards-native source.
- **Item 4 — Second source (messy schema).** A source whose schema deliberately
  differs from FDX, so the normalizer has something hard to map.
- **Item 5 — Normalizer / adapter layer.** One adapter per source mapping raw data
  into the canonical model behind a common interface, with per-adapter tests.
- **Item 6 — Screen-scraping contrast.** A fragile HTML-statement source parsed by
  a scraper adapter, plus a comparison contrasting credential-based scraping with
  token-based FDX access.

### Phase 2 — Consent & traceability (the core)
- **Item 7 — Consent model + enforcement.** The consent lifecycle (granular
  scopes, expiry, grant/revoke) and enforcement so every read is gated on an
  active, in-scope grant.
- **Item 8 — Traceability audit log + data minimization.** An append-only access
  log tied to each grant, plus field-level minimization so a read returns only
  what the granted scopes permit.
- **Item 9 — Consent dashboard (React).** The UI for the consent layer:
  connections, scopes, expiry, one-tap revoke, and the audit log.

### Phase 3 — Aggregation UX
- **Item 10 — Unified accounts + net-worth dashboard (React).** Merged accounts, a
  merged transaction feed, and a household net-worth view — all reads flowing
  through the consent gate.

### Phase 4 — Differentiator
- **Item 11 — Agentic delegation.** A scoped, revocable, fully-logged task
  delegated to an AI agent (surfacing idle cash), modeled as a consent to an agent
  identity: suggestion-only, governed like any other data access.

### Phase 5 — Packaging
- **Item 12 — Test hardening + CI.** Broadened coverage across adapters, consent
  enforcement, and minimization, plus a GitHub Actions workflow (lint, tests,
  frontend build).
- **Item 13 — README, ADRs, and the screen-scraping writeup.** A README framed
  around the regulatory moment, a set of architecture decision records, and a
  standalone explainer on why screen-scraping is being replaced.
- **Item 14 — Project walkthrough.** A concise walkthrough of the problem,
  architecture, the consent layer, and the trade-offs.

**Dependency order:** 1 → 2 → (3, 4) → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14

---

## Follow-on (Items 15–33)

A UI-refinement pass, a technical-hardening pass, and a set of consent-frontier
features — same one-item-per-tag cadence. The two highest-leverage items are the
design foundation (item-15) and the hash chain (item-22); everything else builds
on those.

### Design brief (governs the UI track)

**Subject & job.** The product is *control and evidence* — the user owns their
data, grants scoped access, and can see exactly what was disclosed and what was
withheld. The interface's single job is to make **trust tangible**: precise, calm,
and legible, like a well-kept ledger that happens to be humane.

- **Color — strict and minimal.** Near-monochrome: two neutrals (light + dark) and
  **exactly one accent**, reserved to mean "authorized / active." `withheld` /
  denied is a **muted neutral** — dimmed, outlined, or struck — a *state*, not a
  second hue.
- **Type — technical / financial character.** A monospace/technical face for
  headings, figures, IDs, and audit entries paired with a clean neutral sans for
  body copy. **Tabular figures everywhere** money or data appears.
- **Signature — make the thesis visible, once.** *Minimization made visible:*
  fields the user didn't grant render as explicit `withheld` placeholders with the
  reason; excluded balances show as excluded in net worth, not silently dropped.
- **Anti-defaults.** Minimal risks *bland*, not busy — earn distinction through
  type character, spacing precision, and the `withheld` signature, never by adding
  color.
- **Quality floor (every UI item).** Responsive to ~375px, visible keyboard focus,
  `prefers-reduced-motion` honored, AA contrast in both themes. Copy is design
  material: active voice, sentence case; errors explain the fix, empty states
  invite action.

### Track 1 — UI refinement (Items 15–21)
- **item-15 — Design foundation.** ★ The token system from the brief (color
  light+dark, type scale, spacing, radius, motion) and the restyled app shell —
  the language everything else is written in.
- **item-16 — Dark mode.** A toggle defaulting to system preference, persisting the
  choice, and respecting reduced-motion, on item-15's dark tokens.
- **item-17 — Traceability log controls.** Filter by actor / decision / scope,
  per-column sort, free-text search, a real empty state, and the chain-verified
  badge.
- **item-18 — States & feedback.** Loading skeletons, empty and error states, and
  action feedback — a confirm step and toast on revoke, a toast on grant.
- **item-19 — Overview viz + minimization made visible.** ★ The net-worth
  composition visualized, and the signature: ungranted fields render as explicit
  `withheld` states with reasons; excluded balances appear as excluded.
- **item-20 — "Old way vs new way".** A visual contrast of credential
  screen-scraping vs token-based FDX access, drawn from the scraper source.
- **item-21 — Accessibility & responsive pass.** Keyboard nav + visible focus, AA
  contrast in both themes, aria on controls and charts, correct layout to ~375px,
  reduced motion honored.

### Track 2 — Technical hardening (Items 22–27)
- **item-22 — Tamper-evident hash-chained audit log.** ★ Each entry stores the
  prior entry's hash; `verify_chain()` is exposed and tested against a corrupted
  chain. Append-only *with proof*.
- **item-23 — FAPI-profile OAuth2 on the mock provider.** The mock OAuth2 flow
  upgraded toward FDX's FAPI profile — PKCE (S256) + pushed authorization requests
  (PAR) — with the adapter updated and the covered subset documented.
- **item-24 — Property-based tests on the consent decision.** Hypothesis-generated
  tests asserting "no read without an active, in-scope grant" and "minimization
  never leaks an ungranted field" across thousands of inputs.
- **item-25 — SQLite persistence behind the store seam.** A durable SQLite audit
  backend selectable by config (default in-memory); both backends tested; ADR 0006
  updated.
- **item-26 — Threat model.** Trust boundaries, STRIDE threats/mitigations,
  audit-log integrity, and the accreditation path — `docs/THREAT_MODEL.md`.
- **item-27 — FDX schema conformance validation.** Mock responses and the
  canonical serialization validated against the published FDX JSON schemas; drift
  fails the build.

### Track 3 — Consent-frontier features (Items 28–33)

Forward-looking features that push the consent + traceability thesis onto the
screen. Items 28–31 run on the current mock stack; **items 32–33 are simulations**
— clearly labelled in code and in-product until real integrations exist. Standards
named are alignment targets, not claims of certification.

- **item-28 — Agent activity & authority console.** The delegated agent as a
  visible, revocable object: a live action feed (each read tied to its authorizing
  grant), an authority card (scope, time remaining, Pause / Revoke), an approval
  queue for suggestion-only actions, and an intent → scope preview before granting.
  Revoking halts the feed at once. *Aligns with FDX Agentic-AI principles.*
- **item-29 — Access receipts + permission simulation.** Each audit entry
  re-rendered as a plain-language receipt (who, what cluster/fields, under which
  grant, disclosed vs withheld, a "why" line, JSON export), plus a pre-grant
  preview of which fields a candidate scope would expose vs withhold. *Aligns with
  ISO/IEC TS 27560 / Kantara consent receipts.*
- **item-30 — User-verifiable audit log.** On top of item-22's chain, publishes the
  chain head and a "Verify integrity" control that recomputes the chain
  **in-browser** (Web Crypto) → intact / tampered, plus a "download log + proof"
  export. *Aligns with RFC 6962.*
- **item-31 — Portable alias + consent-gated resolver.** A bank-neutral handle
  (`name.cdb`) that resolves to a **one-time routing token**, never the raw
  institution/transit/account; resolution is consent-gated, re-pointing is a logged
  event, and every resolution lands in the trail.
  *Scope: mock addressing only — no money moves, no registry, no settlement rail.*
- **item-32 — Selective-disclosure attestation (simulated).** Prove a derived fact
  ("holds ≥ $10k in liquid assets") and share only the signed conclusion, not the
  data. *Signed with a symmetric demo key — a demonstration of the pattern, not a
  real zero-knowledge proof. Targets: W3C VC, IETF SD-JWT VC, OID4VP.*
- **item-33 — Verifiable-credential wallet (simulated).** Hold issued attestations
  and present a **selected** subset to a verifier that checks signatures against
  its policy — the OID4VP-style holder → verifier flow, on mock data.
  *A simulated wallet, not a real credential deployment.*

### Dependency reference

`item-15` (foundation — unblocks every UI item) → `item-22` (audit integrity) →
`item-17` (log controls, now with the verified badge) → `item-19` (the signature)
→ `item-16`, `item-18`, `item-20` → `item-21` (final a11y sweep). Then the
hardening items `item-23`–`item-27`, and Track 3: the standouts are `item-28`
(agent console) and `item-31` (portable alias); `item-30` builds directly on
`item-22`, `item-29` pairs with `item-17`, and the simulations `item-32`/`item-33`
come last and stay clearly labelled.

---

## Track 4 — Experience redesign (post-item-33)

A front-end reorganization on top of the finished feature set — same design
language and honest-scope ethos, no backend change (coverage stays at 100%, the
API surface is untouched). Shipped as refinement slices rather than individually
tagged items; the features from Tracks 1–3 are unchanged, but where they live and
how they read is reworked.

- **App shell → sidebar.** The tabbed layout becomes a left **sidebar shell** with
  grouped navigation — the product (Dashboard, Bank Accounts, Control Centre,
  Assistant), a quarantined **Explore (Demo)** group (Portable Address,
  Credentials), and a **Trust & Privacy** group (How it works, Why this is safer,
  Old vs New). The sidebar collapses to an icon rail and carries a page search in
  its header (Claude-style); a top bar holds the title, a **Demo data** pill,
  **Reset demo**, and the theme toggle.
- **Dashboard.** A new at-a-glance landing page — connection/consent/access stats,
  the portable address, recent activity, a "data you've shared" breakdown,
  connected sources, net worth, and log integrity — each tile deep-linking into
  the page that owns it.
- **Control Centre.** The old consent + traceability tab, split into *Connectors*
  (per-source cards with a bank tile, scopes, expiry, revoke, an access preview,
  connect-a-source, and the permission simulator) and *Activity Logs* (the merged
  audit + receipts table). Receipts are rewritten from a key/value dump into a
  plain-language sentence plus four labelled facts (what they saw / kept private /
  under what authority / system note), with a redesigned per-receipt PDF export.
- **Assistant → chat.** The authority console gains a **Chat** view: one
  persistent, scripted (no-LLM) conversation over the consent-gated data, with
  inline delegate/approve actions and a visible **context budget** that compresses
  older turns past a token limit. The console itself moves to an **Activity** tab.
- **Trust & Privacy pages.** The old-vs-new contrast is joined by *How it works*
  (the six-step journey) and *Why this is safer*, grouped as first-run explainers.
- **Aesthetic passes.** A monochrome inline-SVG icon set, on-palette native
  controls, motion on navigation, and a full page-by-page cleanup for a clean,
  minimal, first-time-legible surface.
