# Project Review — 30-minute walkthrough

A delivery script for a project-review interview (a real stage in Wealthsimple's
engineering process). Timings are a guide; leave ~8 minutes for questions. Demo
cues are in **[brackets]**. The goal is to show judgment — *why* it's built this
way — not to narrate every file.

**One-line pitch:** *An FDX-aligned open-banking aggregator whose core product is
a consent + traceability layer — the thing that separates an accredited
participant from a screen scraper — extended to govern an AI agent.*

---

## 0:00 – 3:00 · The problem and the moment

- Most account aggregation in Canada still runs on **screen-scraping and shared
  credentials**: you give an app your bank login, it logs in as you and parses the
  HTML. Two structural problems: it's **brittle** (breaks when the bank restyles a
  page), and it's **all-or-nothing** (no scope, no expiry, no real revocation, no
  consent record).
- This is a documented pain, not a hypothetical — e.g. Wealthsimple's Roundup once
  averaged ~10 failed bank connections a day on scraping aggregators.
- The ground just shifted: **Bill C-15 (Royal Assent March 26, 2026)** replaced
  the original act with a new **Consumer-Driven Banking Act**, oversight moved to
  the **Bank of Canada**, and the technical standard is **FDX** — OAuth2 + FAPI,
  granular time-limited consent, five principles (Control, Access, Transparency,
  Traceability, Security).
- **So I built the other side of that transition**: FDX-first, with consent and an
  auditable access trail as the product, not an afterthought.

> Judgment note to land: I'm honest that Phase-1 timing is uncertain — so I built
> *for* the standard, I don't claim certified connectivity.

## 3:00 – 10:00 · Live demo (the story in three tabs)

**[Open the dashboard.]** One customer, three connected sources — a clean FDX
bank, a messy legacy bank, a screen-scraped "OldBank".

1. **Overview.** Household net worth ($29,328.65), merged accounts grouped by
   source, a merged transaction feed. **[Point at the mortgage.]** It says
   *"balance not shared"* and is **excluded** from net worth — because that
   connection was granted transactions but **not** balances. *Consent, not
   connectivity, decides what you see.*
2. **Consent & Traceability. [Click Revoke on a connection.]** It flips to
   REVOKED instantly, and its data disappears from Overview. **[Scroll the audit
   log.]** Every access — allowed *and* denied — is recorded, tied to the grant,
   showing what was disclosed and what was withheld, and *who* accessed.
3. **Assistant. [Show the delegation, click Run.]** I delegated a scoped,
   revocable task to an agent; it found **$18,010.55** in idle cash and estimates
   **~$414/year** from a move. It **suggests, it never acts.** **[Revoke the
   delegation, click Run → 403.]** No consent, no agent. Its reads are in the same
   audit log, attributed to "🤖 Assistant".

## 10:00 – 15:00 · Architecture

Draw it: **three sources → adapters/normalizer → one canonical FDX model → the
consent gate → dashboards + agent.**

- **Canonical model (FDX-aligned).** Six types; `Decimal` money (never float),
  timezone-aware timestamps, camelCase on the wire. This is the contract
  everything else speaks.
- **Adapters.** One per source, behind a common interface. The FDX source maps
  almost mechanically; the legacy one is the hard case — comma-string money, signed
  amounts, epoch + `DD/MM/YYYY` dates, a nested blob — and the scraper parses HTML.
  Transport is separated from mapping, so the mapping is pure and unit-tested.
- **The gate is the choke point.** Nothing reads data except through a
  `ConsentEnforcingReader`; there is no un-gated path to the adapters.

## 15:00 – 20:00 · The consent layer (the star)

- **`Consent` is behavioral, not a data bag** — granular scopes, expiry,
  revocation — answering `is_active` / `permits` / `covers_account` with one tested
  definition.
- **The gate returns a *reason*** — `NO_CONSENT` / `INACTIVE` / `SCOPE_NOT_GRANTED`
  / `ACCOUNT_NOT_COVERED`. "You never consented" is a different conversation from
  "your consent expired."
- **Traceability + minimization hang off the same reader**: every read is logged
  (append-only), and a read returns only the fields the granted scopes permit — a
  redacted copy, with the withheld clusters recorded in the trail.
- **The differentiator reuses this.** An agent delegation is *just another
  consent*, to an agent identity. That maps one-to-one onto FDX's 2026 Agentic-AI
  themes (agent identity, consent delegation, minimization, downstream
  accountability, traceability). The engine is deterministic today and **swappable
  for an LLM without changing the governance** — which is the point.

## 20:00 – 23:00 · Trade-offs and what production would need

Be the one to raise the limits — it reads as judgment.

- **Mocks + in-memory stores.** Deliberate: demonstrates the architecture with no
  external dependency; the `ConsentStore` / `AuditLog` interfaces are the seam a
  database drops into. (See the ADRs.)
- **For real accreditation, the next steps are clear:**
  - Real **OAuth2 + FAPI** against accredited data providers; proper key
    management and token lifecycle.
  - A **durable, tamper-evident audit store** (append-only, hash-chained) rather
    than an in-memory list.
  - Persistence (Postgres) behind the existing store interfaces; nothing above
    them changes.
  - A **security review** and threat model; secrets management; rate limiting.
  - Multi-currency net worth (FX), entity resolution for accounts seen through
    multiple providers, and pagination on the audit API.
- **What I'd keep exactly as is:** the gate-as-choke-point, `Decimal` money, the
  reason-carrying decisions, and delegation-as-consent.

## 23:00 – 25:00 · Engineering practices

- **100% test coverage**, enforced in CI, with **warnings-as-errors** — a
  financial codebase shouldn't let the untested branch or the silent deprecation
  through. Adapters, consent enforcement, and minimization get the heaviest tests.
- **GitHub Actions** runs lint + tests + coverage gate + the frontend build on
  every push; decisions are recorded as **ADRs**; the history is a tagged timeline
  (`item-01 … item-14`).

## 25:00 – 30:00 · Q&A — anticipated

- **"Why not just use Plaid/Flinks?"** Those are the credential-based plumbing FDX
  is meant to replace. The interesting problem — and the accredited-participant
  differentiator — is the consent/traceability layer, which they don't give you.
- **"Is the gate a real security boundary or a convention?"** It's the only path
  to the adapters, and every read is the gated operation — harder to bypass than a
  per-endpoint decorator someone forgets. In production it'd sit behind
  authn/authz too.
- **"How is the agent 'AI' if it's deterministic?"** It isn't — deliberately. The
  contribution is the *governance* around a delegated actor; the engine is a
  stand-in an LLM slots into without touching the consent/scope/audit rules.
- **"What was the hardest part?"** The normalizer — proving one canonical model can
  absorb an FDX source, a messy legacy schema, and scraped HTML, with the mapping
  pure and fully tested.
- **"What would you do differently?"** Introduce the persistence seam earlier so
  the demo state and a real DB share one interface from day one.

**Close:** *The bet is that in a consumer-driven-banking world, the moat isn't
aggregation — it's trustworthy, auditable consent. That's what I made the core.*
