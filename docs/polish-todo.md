# Follow-on Roadmap — UI Refinement & Technical Hardening

A continuation plan for `cdb-aggregator`. The core build (Items 1–14) is complete;
this covers a UI refinement pass and a set of technical hardening items. It follows
the same cadence as the original build: **one item per session**, in dependency
order, each landing as a tagged commit so history stays a navigable timeline.

## Working rules (every item)
- **One item per session.** Read the existing code first; don't rebuild what works.
- Continue the tag scheme: commit `Item NN — …`, tag `item-NN`, push to `main`.
- Keep **CI green**: backend 100% coverage, ruff clean, frontend build passes.
- Work in this repo only; never open a new one.
- Frontend is **React 18 + Vite**. Match the existing structure and API contract;
  don't change endpoints unless an item says so.

---

## Status & next steps

**Done:** items 15–27 — the full UI refinement track (design system, dark mode, log
controls, states, minimization signature, screen-scraping visual, accessibility) and
the full hardening track (hash-chained audit log, FAPI, property-based tests, SQLite
persistence, threat model, FDX schema conformance). Plus the sanity checkpoint (which
caught and fixed the SQLite-across-the-threadpool bug) and **all of Track 3** —
items 28–33: agent activity & authority console, portable alias + consent-gated
resolver, user-verifiable audit log, access receipts + permission simulation, and the
two clearly-labelled simulations (selective-disclosure attestation, VC wallet).

**Next:** the roadmap is complete. Every item landed as a tagged commit (`item-28` …
`item-33`) with CI green.

### SC — Sanity checkpoint (done, before item-28)

Thirteen items of change — including SQLite persistence (item-25) and the hash chain
(item-22), both of which touch the audit path — is exactly the kind of run where
something drifts. Confirm the project is green and deployable before adding more. This is
a gate, not a build item (no tag); commit any fixes as normal (`fix: …`).

- [x] **CI green on `main`.** The latest `ci.yml` run passes: ruff lint + format, backend
  tests, the 100% coverage gate, and the frontend build.
- [x] **Tests pass locally** at full coverage: `pytest --cov=app --cov-fail-under=100`.
- [x] **Lint/format clean:** `ruff check .` and `ruff format --check .`.
- [x] **Frontend builds:** `cd frontend && npm install && npm run build`.
- [x] **One-service boot works:** build the UI and serve it from FastAPI; confirm the app
  serves the UI, the API under `/api`, and `/docs` on one port.
- [x] **Audit path intact end-to-end** after SQLite + hash chain: grant a consent → do a
  read → revoke → confirm the audit entries are written, the hash chain still verifies,
  and data survives a restart (SQLite durability).
- [x] **Live demo deploys** and the public URL serves current `main` (allow for the free
  tier's cold-start).
- [x] **Tags present:** `git tag` shows `item-15` … `item-27`, each pushed.
- [x] **Fix anything red before proceeding.** The checkpoint caught the SQLite thread-safety
  bug (sync handlers run across the ASGI threadpool); fixed in `fix: make SqliteAuditLog
  safe across the server's threadpool` before item-28.

**Kickoff prompt:**
> cdb-aggregator, **sanity checkpoint before item-28 — do not build a feature**. Verify
> the project is green and deployable after items 15–27. Run: `ruff check .` and
> `ruff format --check .`; `pytest --cov=app --cov-fail-under=100`; and a frontend build
> (`cd frontend && npm install && npm run build`). Boot the one-service mode (UI served by
> FastAPI) and confirm the UI, the API under `/api`, and `/docs` all respond. Exercise the
> audit path end-to-end: grant a consent → do a read → revoke → confirm audit entries are
> written, the hash chain verifies, and data survives a restart (SQLite durability).
> Confirm the latest `ci.yml` run on `main` is green, the live demo serves current `main`,
> and `git tag` shows `item-15` … `item-27`. Report anything red and fix it with a `fix:`
> commit before we start item-28.

### Order built (after SC) — all done

1. ✅ **item-28 — agent activity & authority console** (Track 3 standout; builds on Item 11).
2. ✅ **item-31 — portable alias + consent-gated resolver** (the
   route-on-a-lookup / portable-address feature).
3. ✅ **item-30 — user-verifiable audit log** (built on item-22's hash chain).
4. ✅ **item-29 — access receipts + permission simulation** (pairs with item-17).
5. ✅ **item-32, item-33 — simulated selective-disclosure + VC wallet** (clearly labelled
   as simulations, in code and in-product).

### Housekeeping (independent of the above)

- [x] **Neutralize the `docs/` folder for public view.** Done: `docs/research-report.md`
  and `docs/build-todo.md` replaced with the neutral versions, employer-specific language
  stripped repo-wide (incl. code comments), and `docs/blog-post.md` removed.

---

## DESIGN BRIEF (read before any UI item — this governs the whole UI track)

**Subject & job.** A Consumer-Driven Banking aggregator whose real product is
*control and evidence* — the user owns their data, grants scoped access, and can see
exactly what was disclosed and what was withheld. The interface's single job is to
make **trust tangible**: precise, calm, and legible, like a well-kept ledger that
happens to be humane.

**Aesthetic direction: modern + minimal.** Restraint over decoration. Generous
whitespace, content first, near-monochrome, strong hierarchy, nothing on the screen
that isn't doing a job. The feeling is *confident and quiet* — the design earns trust
by looking considered and uncluttered, not by adding visual interest. When in doubt,
remove something.

**Do a design plan first, then build (item-15).** Before writing UI code, produce a
compact token system and get it right, because everything downstream inherits it:
- **Color — strict and minimal.** Near-monochrome. A neutral base (clean off-white
  and near-black for the two themes) plus **exactly one accent**, a calm, considered
  hue reserved to mean "authorized / active." **No second bright color.** `withheld`
  / denied is shown as a **muted neutral** — dimmed, outlined, or struck — a *state*,
  not a new hue. Target roughly **2 neutrals + 1 accent, full stop**; more colors than
  that is precisely what to avoid. Define values for both light and dark up front.
- **Type — technical / financial character.** Lead with a **monospace or precise
  technical face** for headings, figures, IDs, and audit entries — a "code / ledger"
  feel (e.g. JetBrains Mono, IBM Plex Mono, or an SF Mono-like face), paired with a
  clean neutral sans (e.g. Inter or IBM Plex Sans) for any running body copy.
  **Tabular figures everywhere money or data appears** — columns must align. Type is
  the personality here: since color is held to almost nothing, the restraint is bought
  back as precision and character in the type.
- **Layout & signature:** pick the **one** memorable element and spend restraint's
  counterweight there (see below); keep everything else quiet.

**Signature (make it count, once).** Make the thesis *visible*. Two candidates — pick
and commit to one as the primary:
1. **Minimization made visible.** Fields the user didn't grant don't just vanish —
   they render as explicit `withheld` placeholders with the reason, so the user *sees*
   the gate working in their favor. Excluded balances show as excluded in net worth,
   not silently dropped.
2. **The audit trail as a spine.** Traceability isn't a buried table; it's a
   first-class, always-legible record of who-read-what-under-which-grant.

**Anti-defaults.** Minimal is the brief, so the real risk is **bland**, not busy —
earn distinction through type character (the mono/technical treatment), spacing
precision, tabular figures, and the `withheld` signature, **never by adding color**.
Keep the single accent calm and meaningful (not a trendy acid-green or vermilion).
Avoid warm-cream + serif + terracotta, and avoid dense broadsheet hairline layouts.
If the design plan drifts toward a generic look, revise it and say what changed.

**Quality floor (every UI item).** Responsive to ~375px, visible keyboard focus,
`prefers-reduced-motion` respected, AA contrast. Copy is design material: active
voice, sentence case, name things by what the user controls; errors explain the fix,
empty states invite action. A "Revoke" button produces a "Revoked" confirmation.

---

## Track 1 — UI refinement

### [x] item-15 — Design foundation: identity + token system  ★ do first
**Produces:** the token system from the brief implemented as CSS variables / theme
(color light+dark, type scale, spacing, radius, motion), the display/body/mono faces
wired in, and the app shell (nav, layout, the three tabs) restyled to it. No feature
changes — this is the language everything else is written in.
**Depends on:** the existing frontend.
**Kickoff prompt:**
> cdb-aggregator, **item-15 — design foundation**. Read the DESIGN BRIEF in
> docs/polish-todo.md, then the existing frontend. FIRST produce a design plan (named
> palette for light+dark, type pairing led by a technical/mono face, layout concept,
> and the ONE signature element) and self-critique it against the anti-defaults —
> revise anything that reads generic and say what you changed. THEN implement it as a
> token system + theme and restyle the app shell and the three tabs to it. No
> API/feature changes. Keep CI green. Commit `Item 15 — design foundation and token system`, tag `item-15`, push.

### [x] item-16 — Dark mode
**Produces:** a light/dark toggle that defaults to system preference, persists the
choice, and animates the switch under `prefers-reduced-motion` guards. Uses the dark
tokens from item-15 (no new colors invented here).
**Depends on:** item-15.
**Kickoff prompt:**
> cdb-aggregator, **item-16 — dark mode**. Using the dark tokens from item-15, add a
> theme toggle: default to system preference, persist the user's choice, respect
> prefers-reduced-motion. Verify contrast holds in both themes. Commit `Item 16 — dark mode`, tag `item-16`, push.

### [x] item-17 — Traceability log: filter, sort, search
**Produces:** the audit-log view upgraded to real controls — filter by **actor**
(aggregator vs delegated agent), by **decision** (allowed / denied), and by **scope**;
**per-column sort** (ascending/descending) on time and actor; and free-text **search**.
A real empty / `no matches` state in the interface's voice. If the integrity check
from item-22 exists, surface a "chain verified ✓ / broken" badge here.
**Depends on:** item-15 (pairs with item-22).
**Kickoff prompt:**
> cdb-aggregator, **item-17 — traceability log controls**. Upgrade the audit-log UI:
> filter by actor (aggregator vs agent), decision (allowed/denied), and scope;
> per-column ascending/descending sort on timestamp and actor; free-text search. Keep
> it fast and legible per the design foundation; write a real empty-results state. If
> a chain-verification endpoint exists, show a verified/broken badge. Commit
> `Item 17 — audit log filter, sort, search`, tag `item-17`, push.

### [x] item-18 — States & feedback
**Produces:** loading skeletons, empty states, and error states across the three tabs,
plus action feedback — a toast on grant/revoke, and a confirm step on revoke. All copy
in the interface's voice (active, specific, no apologies).
**Depends on:** item-15.
**Kickoff prompt:**
> cdb-aggregator, **item-18 — states and feedback**. Add loading skeletons, empty
> states, and error states (explain the fix, don't apologize) across Overview /
> Consent / Assistant. Add a confirm step and a "Revoked" toast on revoke, and a toast
> on new grants. Match the design foundation. Commit `Item 18 — loading, empty, error, and action states`, tag `item-18`, push.

### [x] item-19 — Overview data viz + minimization made visible  ★ the signature
**Produces:** the Overview's net-worth composition as a clear visualization, and the
signature element from the brief: withheld/excluded fields render as explicit
`withheld` states (with reason), and excluded balances show as excluded in net worth —
the gate working *for* the user, made visible.
**Depends on:** item-15.
**Kickoff prompt:**
> cdb-aggregator, **item-19 — overview viz + minimization made visible**. Visualize
> household net-worth composition, and implement the signature: fields not granted
> render as explicit `withheld` placeholders with their reason; excluded balances
> appear as excluded (not silently dropped) in net worth. Keep it calm and precise per
> the foundation. Commit `Item 19 — net-worth viz and visible minimization`,
> tag `item-19`, push.

### [x] item-20 — "Old way vs new way" screen-scraping visual
**Produces:** a visual contrast (in-app or a dedicated view) dramatizing
credential-based screen-scraping vs token-based FDX access — pulling from the existing
scraper source and docs/screen-scraping.md.
**Depends on:** item-15.
**Kickoff prompt:**
> cdb-aggregator, **item-20 — old-way/new-way visual**. Build a visual comparison of
> credential screen-scraping vs token-based FDX access, drawing on the scraper provider
> and docs/screen-scraping.md. Match the design foundation. Commit `Item 20 — screen-scraping vs FDX visual`, tag `item-20`, push.

### [x] item-21 — Accessibility & responsive pass
**Produces:** a cross-cutting sweep — keyboard navigation and visible focus on every
interactive element, AA contrast verified in both themes, aria labels on the log
controls and charts, layout correct down to ~375px, reduced-motion honored.
**Depends on:** the UI items above.
**Kickoff prompt:**
> cdb-aggregator, **item-21 — a11y and responsive pass**. Sweep the whole UI: keyboard
> nav + visible focus, AA contrast in both themes, aria on log controls and charts,
> correct layout to ~375px, prefers-reduced-motion honored. Note anything that can't be
> fixed without a redesign. Commit `Item 21 — accessibility and responsive pass`,
> tag `item-21`, push.

---

## Track 2 — Technical hardening

### [x] item-22 — Tamper-evident (hash-chained) audit log  ★ high value
**Produces:** each audit entry stores the hash of the prior entry, so any alteration or
deletion breaks the chain. A `verify_chain()` exposed via an endpoint and asserted in
tests (happy path + a deliberately corrupted chain). Pairs with item-17's verified
badge.
**Why:** traceability is the core of the system; a hash chain upgrades the audit log
from append-only *by convention* to append-only *with proof* — you can demonstrate no
entry was changed after the fact.
**Depends on:** the existing audit log (Item 8).
**Kickoff prompt:**
> cdb-aggregator, **item-22 — hash-chained audit log**. Make the append-only audit log
> tamper-evident: each entry stores the prior entry's hash; add verify_chain(), expose
> it, and test the happy path and a corrupted chain. Keep 100% coverage. Commit
> `Item 22 — tamper-evident hash-chained audit log`, tag `item-22`, push.

### [x] item-23 — FAPI-profile OAuth2 on the mock provider
**Produces:** the mock FDX bank's OAuth2 flow upgraded toward the **FAPI** security
profile FDX specifies — PKCE, pushed authorization requests (PAR), and/or
sender-constrained tokens — with the adapter updated to match, and docs stating which
subset of FAPI is covered vs. out of scope.
**Why:** FDX mandates the FAPI profile, so building to it makes the mock provider a
faithful stand-in for a real data provider and exercises the security-critical path
properly rather than with a toy token flow.
**Depends on:** the mock provider (Item 3) and the consent layer (Item 7).
**Kickoff prompt:**
> cdb-aggregator, **item-23 — FAPI-profile OAuth2**. Read the mock_fdx_bank provider
> and the adapter. Upgrade the mock OAuth2 flow toward the FAPI profile: add PKCE and
> pushed authorization requests (and sender-constrained tokens if tractable), update
> the adapter, and document which subset of FAPI is covered vs not. Full tests, 100%
> coverage. Commit `Item 23 — FAPI-profile OAuth2 on mock provider`, tag `item-23`,
> push.

### [x] item-24 — Property-based tests on the consent decision
**Produces:** Hypothesis-style generative tests over the consent gate and the
normalizer, asserting the invariants **"a read is never allowed without an active,
in-scope grant"** and **"minimization never leaks an ungranted field,"** across
thousands of randomized inputs.
**Why:** the consent decision is the security-critical invariant of the whole system;
generative testing hardens it against edge cases that example-based unit tests miss.
**Depends on:** the consent gate (Item 7) and minimization (Item 8).
**Kickoff prompt:**
> cdb-aggregator, **item-24 — property-based consent tests**. Add Hypothesis to dev
> deps. Write generative tests over the consent gate and normalizer that assert: no
> read without an active in-scope grant, and no ungranted field ever appears in output.
> Keep coverage at 100%. Commit `Item 24 — property-based tests on consent + minimization`, tag `item-24`, push.

### [x] item-25 — SQLite persistence behind the store seam
**Produces:** one concrete store (SQLite) implemented against the existing in-memory
store interface, selectable by config and defaulting to in-memory, with the audit log
prioritized for durability. ADR 0006 updated; tests cover both backends.
**Why:** demonstrates that the store interface is a real seam, and makes the audit
trail durable across restarts — which matters for a log whose value is that it persists.
**Depends on:** the existing store interfaces (pairs well with item-22).
**Kickoff prompt:**
> cdb-aggregator, **item-25 — SQLite persistence**. Implement a SQLite-backed store
> against the existing store interface, selected via CDB_ config, defaulting to
> in-memory. Prioritize a durable audit log. Update ADR 0006. Tests cover both
> backends; 100% coverage. Commit `Item 25 — SQLite persistence behind store seam`,
> tag `item-25`, push.

### [x] item-26 — THREAT_MODEL.md
**Produces:** a concise threat-model document — trust boundaries, token and consent
handling, audit-log integrity, and what a production accreditation path would require.
Linked from the README's security area.
**Why:** for a system whose whole point is consent and traceability, documenting the
trust boundaries and integrity guarantees is part of building security-critical
software responsibly, and records the reasoning behind the design.
**Depends on:** nothing new.
**Kickoff prompt:**
> cdb-aggregator, **item-26 — THREAT_MODEL.md**. Write docs/THREAT_MODEL.md: trust
> boundaries, token/consent threats and mitigations, audit-log integrity, and a short
> "what real FDX accreditation would require" section. Link it from the README security
> area. Commit `Item 26 — threat model`, tag `item-26`, push.

### [x] item-27 — FDX schema conformance validation
**Produces:** the mock providers' responses and the canonical model's serialization
validated against the **published FDX JSON schemas** for the entities modeled
(accounts, balances, transactions, investment holdings, customer), with a conformance
test that fails loudly on drift, and docs stating which entities/fields are covered vs
out of scope.
**Why:** moves the project's strongest claim from *FDX-aligned* to *FDX-conformant* on
the covered surface — provider responses and canonical output are checked against the
actual standard, not a hand-rolled approximation of it.
**Depends on:** the canonical model (Item 2) and the mock providers (Items 3–4).
**Kickoff prompt:**
> cdb-aggregator, **item-27 — FDX schema conformance**. Pull the FDX API JSON schemas
> for the entities we model; validate the mock FDX provider's responses and our
> canonical serialization against them; add a conformance test that fails on drift.
> Document which entities/fields are covered vs out of scope. Keep 100% coverage.
> Commit `Item 27 — FDX schema conformance validation`, tag `item-27`, push.

---

## Track 3 — Advanced / consent-frontier features

Higher-effort, forward-looking features that extend the consent + traceability thesis
onto the screen. **item-28 to item-31 are buildable on the current mock/in-memory
stack; item-32 and item-33 are staged** — simulated and clearly labelled as such until
real integrations exist. Standards named below are alignment targets, not claims of
certification. (Two smaller touches from the same research — consent expiry/renewal
countdowns and a small source→adapter→gate→screen data-flow animation — are best folded
into item-18 and item-19 rather than built as separate items.)

### [x] item-28 — Agent activity & authority console
**Produces:** a live view of the delegated agent acting under a scoped grant — a
real-time action feed (each row: intent, the field/account read, the grant that
authorized it, timestamp, status); an **authority card** (agent identity, scope held,
time remaining, Pause / Revoke now); and an **approval queue** for suggestion-only
actions (Approve / Reject / Request changes). Includes an **intent → scope preview**:
before a grant is minted, show exactly what the agent will and won't be able to see.
Revoking must halt the feed immediately.
**Why:** makes delegated authority a first-class, visible, revocable object rather than
an opaque background process; extends the agent feature (Item 11) with real-time
accountability. Aligns with FDX's Agentic AI guiding principles (agent identity, consent
delegation, data minimization, downstream accountability, traceability).
**Depends on:** the agent feature (Item 11) and the consent gate (Item 7).
**Align with:** FDX Agentic AI principles; OAuth 2.0 token exchange (RFC 8693, `act` claim).
**Kickoff prompt:**
> cdb-aggregator, **item-28 — agent activity & authority console**. Read the agent
> (Item 11) and consent code. Add a live action feed (intent, field read, authorizing
> grant, timestamp, status) over SSE or polling; an authority card (identity, scope,
> time remaining, Pause/Revoke); an approval queue for suggestion-only actions; and an
> intent→scope preview before granting. Revoke halts the feed immediately. Keep 100%
> backend coverage, CI green.
> Commit `Item 28 — agent activity and authority console`, tag `item-28`, push.

### [x] item-29 — Access receipts + permission simulation
**Produces:** (a) an **access receipt** for every read — who accessed, what field/cluster,
the authorizing grant, purpose, timestamp, what was disclosed vs withheld, and a short
"why this was accessed" line — as a scrollable receipt history with a per-receipt detail
view and a machine-readable JSON export; (b) a **permission simulation** that previews,
before granting, exactly which fields a candidate scope would expose vs. withhold,
computed against the mock data.
**Why:** turns the audit log into a consumer-legible artifact and turns consent from a
blind checkbox into an informed preview — direct expressions of transparency and
minimization.
**Depends on:** the audit log + minimization (Item 8); pairs with the log UI (item-17).
**Align with:** ISO/IEC TS 27560 (consent-receipt structure); Kantara Consent Receipt.
**Kickoff prompt:**
> cdb-aggregator, **item-29 — access receipts + permission simulation**. Render each
> audit entry as an access receipt (who, what field/cluster, authorizing grant, purpose,
> disclosed vs withheld, a "why accessed" line) with a detail view and JSON export. Add a
> permission simulator that, for a candidate scope, shows which fields would be visible
> vs withheld against the mock data. Match the design foundation; keep coverage at 100%.
> Commit `Item 29 — access receipts and permission simulation`, tag `item-29`, push.

### [x] item-30 — User-verifiable audit log (in-browser)
**Produces:** on top of item-22's hash chain, a published **chain head** (latest hash)
and a **"Verify integrity"** control in the traceability view that recomputes the chain
in-browser (Web Crypto) and reports intact / tampered, plus a "download log + proof"
export so the chain can be checked independently. Optionally sign the chain head with a
demo key.
**Why:** moves the audit log from append-only *by assertion* to append-only *the user
can verify themselves* — the visible payoff of item-22.
**Depends on:** the hash-chained log (item-22) and the log UI (item-17).
**Align with:** RFC 6962 (transparency-log construction); ISO/IEC 27560 for the record shape.
**Kickoff prompt:**
> cdb-aggregator, **item-30 — user-verifiable audit log**. Using item-22's hash chain,
> publish the chain head and add a "Verify integrity" control that recomputes the chain
> in-browser via Web Crypto and shows intact/tampered, plus a "download log + proof"
> export. Optionally sign the chain head with a demo key. Test the verifier against a
> tampered fixture. Keep coverage at 100%.
> Commit `Item 30 — user-verifiable audit log`, tag `item-30`, push.

### [x] item-31 — Portable account alias + consent-gated resolver
**Produces:** a bank-neutral **alias** the user owns (e.g. `name.cdb`) plus a **resolver**
mapping it to current account coordinates, with four properties: (1) resolution is
**consent-gated** — a lookup returns nothing without an active, in-scope grant; (2) the
resolver returns a **one-time routing token**, never the raw institution/transit/account,
so a counterparty never learns the user's bank or branch; (3) **re-pointing** the alias to
a different (mock) source is a scoped, logged event — portability expressed as a consent
action; (4) every resolution, allowed or denied, is written to the traceability trail.
UI: a **"portable address" card** — current routing target, a change-bank action, and
"who resolved this, when, and what they were told."
**Why:** demonstrates the "route on a lookup, not on the identifier" pattern (as used by
mobile-number portability and alias-based payment schemes), applied with consent,
minimization, and traceability. It reframes account portability and the account-number
privacy leak as an addressing problem the consent layer already solves.
**Depends on:** the consent gate (Item 7), the audit log (Item 8), and the canonical
model (Item 2).
**Scope note:** demonstrates the *addressing/portability pattern* on mock data. It does
not move real money, is not a real central registry, and does not settle over any payment
rail — the same honest-scope line the rest of the project draws.
**Kickoff prompt:**
> cdb-aggregator, **item-31 — portable alias + consent-gated resolver**. Add a
> bank-neutral alias registry (handle → account) and a resolver endpoint that: returns
> nothing without an active in-scope grant; returns a one-time routing token, never raw
> institution/transit/account; treats re-pointing an alias to a different source as a
> scoped, logged event; and writes every resolution (allowed or denied) to the audit
> trail. Add a "portable address" card (current target, change bank, resolution history).
> Document the scope limits (mock addressing only; no settlement). Keep coverage at 100%.
> Commit `Item 31 — portable alias and consent-gated resolver`, tag `item-31`, push.

### Staged (simulated — label clearly; graduate only with real integrations)

### [x] item-32 — Selective-disclosure attestation (simulated)
**Produces:** a "prove without sharing" flow that issues a signed attestation of a
derived fact (e.g. a threshold check such as *balance stayed non-negative for 90 days*)
without exposing the underlying transactions — computed server-side from mock data and
labelled clearly in-product as a simulation of zero-knowledge / selective disclosure.
**Why:** demonstrates minimization taken to its limit — share a conclusion, not the data.
**Depends on:** the canonical model (Item 2) and consent (Item 7).
**Align with (target):** W3C Verifiable Credentials; IETF SD-JWT VC; OpenID for Verifiable
Presentations (OID4VP).
**Scope note:** the attestation is computed and signed server-side on mock data — a
demonstration of the pattern, not a real zero-knowledge proof. Graduate to real SD-JWT VC
/ range proofs only with real data and infrastructure.
**Kickoff prompt:**
> cdb-aggregator, **item-32 — simulated selective-disclosure attestation**. Add a flow
> that issues a signed attestation of a derived fact (e.g. a threshold check) without
> exposing the underlying transactions, computed server-side from mock data. Label it
> clearly in-product as a simulation of zero-knowledge / selective disclosure, and
> document what a real implementation would require. Keep coverage at 100%.
> Commit `Item 32 — simulated selective-disclosure attestation`, tag `item-32`, push.

### [x] item-33 — Verifiable-credential wallet view (simulated)
**Produces:** a holder-style wallet view where issuer-signed attestations derived from
the user's (mock) financial data can be selectively presented to a verifier — a simulated
wallet, clearly labelled.
**Why:** demonstrates user-held, selectively-disclosed credentials — the direction open
finance and digital-identity wallets are heading.
**Depends on:** item-32.
**Align with (target):** W3C Verifiable Credentials; OID4VCI / OID4VP; eIDAS 2.0 / EUDI
wallet patterns.
**Scope note:** a simulated wallet on mock data; not a real credential wallet or
issuer/verifier deployment.
**Kickoff prompt:**
> cdb-aggregator, **item-33 — simulated VC wallet view**. Add a holder-style wallet view
> presenting issuer-signed attestations (from item-32) selectively to a verifier, on mock
> data, clearly labelled as a simulation. Document what real OID4VP/VC infrastructure
> would require. Keep coverage at 100%.
> Commit `Item 33 — simulated verifiable-credential wallet`, tag `item-33`, push.

---

## Dependency reference

> Live status and the current working order are in **Status & next steps** at the top of
> this file. This section records the underlying dependency rationale (why the order is
> what it is), for reference.

`item-15` (foundation — unblocks every UI item) → `item-22` (audit integrity) →
`item-17` (log controls, now with the verified badge) → `item-19` (the signature) →
`item-16`, `item-18`, `item-20` → `item-21` (final a11y sweep).

Then depth and frontier items as time allows: `item-23`–`item-27` (hardening and
conformance), and Track 3. Within Track 3 the two standouts are **`item-28`** (agent
activity & authority console) and **`item-31`** (portable alias + resolver);
**`item-30`** builds directly on `item-22`, and **`item-29`** pairs with `item-17`. The
simulated items (`item-32`, `item-33`) come last and must stay clearly labelled.

The design foundation and the hash chain remain the two highest-leverage items; do those
first.
