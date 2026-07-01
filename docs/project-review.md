# Project tour

A guided read of `cdb-aggregator`: what it is, what it does, how it's built, and
the judgment behind it. The one-line version:

> *An FDX-aligned open-banking aggregator whose core product is a consent +
> traceability layer — the thing that separates an accredited participant from a
> screen scraper — extended to govern an AI agent.*

For the full item-by-item build history see [`roadmap.md`](roadmap.md); for the
regulatory background see [`research-report.md`](research-report.md).

---

## The problem and the moment

Most account aggregation in Canada still runs on **screen-scraping and shared
credentials**: you hand an app your bank login, it logs in as you and parses the
HTML. That has two structural problems. It's **brittle** — it breaks whenever the
bank restyles a page (scraping-based aggregators have reported on the order of ten
failed bank connections a day) — and it's **all-or-nothing**: no scope, no expiry,
no real revocation, and no consent record.

The ground has shifted. **Bill C-15 received Royal Assent on March 26, 2026**,
replacing the original act with a new **Consumer-Driven Banking Act**, with
oversight moving to the **Bank of Canada**. The technical standard is **FDX** —
OAuth 2.0 + FAPI, granular time-limited consent, and five principles: Control,
Access, Transparency, Traceability, Security.

This project is the other side of that transition: **FDX-first, with consent and
an auditable access trail as the product, not an afterthought.** It's honest that
Phase-1 timing is still uncertain — so it's built *for* the standard rather than
claiming certified connectivity.

## What the app does — a tour

The demo seeds one customer with three connected sources of deliberately different
shape: a clean FDX bank, a messy legacy bank, and a screen-scraped "OldBank".
Everything reads through the consent gate. There are six tabs.

- **Overview** shows household net worth ($29,328.65), merged accounts grouped by
  source, and a merged transaction feed. The mortgage reads *"balance not shared"*
  and is **excluded** from net worth — its connection was granted transactions but
  **not** balances. Consent, not connectivity, decides what you see.
- **Consent & Traceability** lists the connections; revoking one flips it to
  REVOKED instantly and its data disappears from Overview. The audit log records
  every access — allowed *and* denied — tied to the grant it relied on, showing
  what was disclosed and what was withheld, and *who* accessed. The log is a
  SHA-256 hash chain, and a **"Verify integrity"** control recomputes every link
  **in the browser** (Web Crypto) — append-only you can check, not just assert.
  Below it, **access receipts** re-render each access in plain language, and a
  **permission simulator** previews what a scope would share before you grant it.
- **Assistant** delegates a scoped, revocable task to an agent; it finds
  **$18,010.55** in idle cash and estimates **~$414/year** from a move. It
  **suggests, it never acts** — each run lands in an **approval queue**, and an
  **authority console** streams the agent's reads with a Pause / Revoke card.
  Revoke the delegation and a run returns `403`: no consent, no agent. Its reads
  sit in the same audit log, attributed to the assistant.
- **Portable address** gives the user a bank-neutral alias (`ada.cdb`) that
  resolves to a **one-time routing token** — never the bank, branch, or account
  number. Resolution is consent-gated: revoke the target account's grant and the
  same lookup returns nothing.
- **Old vs New** is a side-by-side contrast of credential screen-scraping and
  token-based FDX access.
- **Credentials** *(labelled a simulation)* proves a derived fact — "holds ≥ $10k
  in liquid assets" — and shares only the signed conclusion, not the balances. The
  attestation goes into a wallet and a **selected** subset can be presented to a
  verifier, which rejects a tampered copy on its signature.

## Architecture

The data flow is **three sources → adapters / normalizer → one canonical FDX
model → the consent gate → dashboards + agent.**

- **Canonical model (FDX-aligned).** Six types; `Decimal` money (never float),
  timezone-aware timestamps, camelCase on the wire. This is the contract
  everything else speaks.
- **Adapters.** One per source, behind a common interface. The FDX source maps
  almost mechanically; the legacy one is the hard case — comma-string money, signed
  amounts, epoch + `DD/MM/YYYY` dates, a nested blob — and the scraper parses HTML.
  Transport is separated from mapping, so the mapping stays pure and unit-tested.
- **The gate is the choke point.** Nothing reads data except through a
  `ConsentEnforcingReader`; there is no un-gated path to the adapters.

## The consent layer — the core

- **`Consent` is behavioral, not a data bag.** Granular scopes, expiry, and
  revocation are answered by `is_active` / `permits` / `covers_account`, each with
  one tested definition.
- **The gate returns a *reason*** — `NO_CONSENT` / `INACTIVE` / `SCOPE_NOT_GRANTED`
  / `ACCOUNT_NOT_COVERED`. "You never consented" is a different conversation from
  "your consent expired."
- **Traceability and minimization hang off the same reader.** Every read is logged
  append-only, and a read returns only the fields the granted scopes permit — a
  redacted copy, with the withheld clusters recorded in the trail.
- **The differentiator reuses all of this.** An agent delegation is *just another
  consent*, to an agent identity — which maps one-to-one onto FDX's 2026
  Agentic-AI themes (agent identity, consent delegation, minimization, downstream
  accountability, traceability). The engine is deterministic today and swappable
  for an LLM **without changing the governance**, which is the point.

## Trade-offs and the path to production

The limits are deliberate and worth stating plainly.

- **Mocks + in-memory stores.** They demonstrate the architecture with no external
  dependency; the `ConsentStore` / `AuditLog` interfaces are the seam a database
  drops into (see the [ADRs](adr/)). A SQLite backend already sits behind that seam
  for the audit log.
- **For real accreditation, the next steps are clear:**
  - Real **OAuth 2.0 + FAPI** against accredited data providers, with proper key
    management and token lifecycle.
  - A **durable, tamper-evident audit store** (append-only, hash-chained,
    externally anchored) rather than an in-memory list.
  - Persistence (e.g. Postgres) behind the existing store interfaces — nothing
    above them changes.
  - A full **security review** and threat model, secrets management, and rate
    limiting.
  - Multi-currency net worth (FX), entity resolution for accounts seen through
    multiple providers, and pagination on the audit API.
- **What stays exactly as is:** the gate-as-choke-point, `Decimal` money, the
  reason-carrying decisions, and delegation-as-consent.

## Engineering practices

- **100% backend test coverage**, enforced in CI, with **warnings-as-errors** — a
  financial codebase shouldn't let an untested branch or a silent deprecation
  through. Adapters, consent enforcement, and minimization carry the heaviest
  tests, alongside property-based tests over the consent invariants.
- **GitHub Actions** runs lint + tests + the coverage gate + the frontend build on
  every push; decisions are recorded as **ADRs**; and the history is a tagged
  timeline (`item-01 … item-33` — the core build plus the UI-refinement,
  hardening, and consent-frontier follow-on).

## Anticipated questions

- **Why not just use Plaid / Flinks?** Those are the credential-based plumbing FDX
  is meant to replace. The interesting problem — and the accredited-participant
  differentiator — is the consent / traceability layer, which they don't provide.
- **Is the gate a real security boundary or a convention?** It's the only path to
  the adapters, and every read is the gated operation — harder to bypass than a
  per-endpoint decorator someone forgets. In production it would sit behind
  authentication and authorization as well.
- **How is the agent "AI" if it's deterministic?** It isn't, deliberately. The
  contribution is the *governance* around a delegated actor; the engine is a
  stand-in an LLM slots into without touching the consent / scope / audit rules.
- **What was the hardest part?** The normalizer — proving one canonical model can
  absorb an FDX source, a messy legacy schema, and scraped HTML, with the mapping
  pure and fully tested.
- **What would you do differently?** Introduce the persistence seam earlier, so the
  demo state and a real database share one interface from day one.

The bet behind the design: in a consumer-driven-banking world, the moat isn't
aggregation — it's trustworthy, auditable consent. That's what the project makes
its core.
