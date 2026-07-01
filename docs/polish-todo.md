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

### [ ] item-15 — Design foundation: identity + token system  ★ do first
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

### [ ] item-16 — Dark mode
**Produces:** a light/dark toggle that defaults to system preference, persists the
choice, and animates the switch under `prefers-reduced-motion` guards. Uses the dark
tokens from item-15 (no new colors invented here).
**Depends on:** item-15.
**Kickoff prompt:**
> cdb-aggregator, **item-16 — dark mode**. Using the dark tokens from item-15, add a
> theme toggle: default to system preference, persist the user's choice, respect
> prefers-reduced-motion. Verify contrast holds in both themes. Commit `Item 16 — dark mode`, tag `item-16`, push.

### [ ] item-17 — Traceability log: filter, sort, search
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

### [ ] item-18 — States & feedback
**Produces:** loading skeletons, empty states, and error states across the three tabs,
plus action feedback — a toast on grant/revoke, and a confirm step on revoke. All copy
in the interface's voice (active, specific, no apologies).
**Depends on:** item-15.
**Kickoff prompt:**
> cdb-aggregator, **item-18 — states and feedback**. Add loading skeletons, empty
> states, and error states (explain the fix, don't apologize) across Overview /
> Consent / Assistant. Add a confirm step and a "Revoked" toast on revoke, and a toast
> on new grants. Match the design foundation. Commit `Item 18 — loading, empty, error, and action states`, tag `item-18`, push.

### [ ] item-19 — Overview data viz + minimization made visible  ★ the signature
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

### [ ] item-20 — "Old way vs new way" screen-scraping visual
**Produces:** a visual contrast (in-app or a dedicated view) dramatizing
credential-based screen-scraping vs token-based FDX access — pulling from the existing
scraper source and docs/screen-scraping.md.
**Depends on:** item-15.
**Kickoff prompt:**
> cdb-aggregator, **item-20 — old-way/new-way visual**. Build a visual comparison of
> credential screen-scraping vs token-based FDX access, drawing on the scraper provider
> and docs/screen-scraping.md. Match the design foundation. Commit `Item 20 — screen-scraping vs FDX visual`, tag `item-20`, push.

### [ ] item-21 — Accessibility & responsive pass
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

### [ ] item-22 — Tamper-evident (hash-chained) audit log  ★ high value
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

### [ ] item-23 — FAPI-profile OAuth2 on the mock provider
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

### [ ] item-24 — Property-based tests on the consent decision
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

### [ ] item-25 — SQLite persistence behind the store seam
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

### [ ] item-26 — THREAT_MODEL.md
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

### [ ] item-27 — FDX schema conformance validation
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

## Suggested order
`item-15` (foundation — unblocks every UI item) → `item-22` (audit integrity) →
`item-17` (log controls, now with the verified badge) → `item-19` (the signature) →
`item-16`, `item-18`, `item-20` → `item-21` (final a11y sweep). Then `item-23`–`item-27`
as depth allows. The design foundation and the hash chain are the two highest-leverage
items; do those first.
