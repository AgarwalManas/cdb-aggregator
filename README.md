# Consumer-Driven Banking Aggregator

[![CI](https://github.com/AgarwalManas/cdb-aggregator/actions/workflows/ci.yml/badge.svg)](https://github.com/AgarwalManas/cdb-aggregator/actions/workflows/ci.yml)

An **FDX-aligned account aggregator** for Canada's Consumer-Driven Banking era,
built around a **first-class consent and traceability layer** — the part that
separates an accredited open-banking participant from a credential-storing screen
scraper.

It ingests data from three deliberately different mock sources, normalizes them
into one FDX-shaped model, and gates **every read** on an active, in-scope,
revocable consent — logging each access to an append-only, hash-chained trail and
returning only the fields the customer actually shared. On top of that sits a
unified net-worth dashboard and an agentic-delegation layer that hands a
**scoped, revocable, fully-logged** task to an AI agent.

From there it pushes the consent thesis onto the screen — a real-time
**agent authority console**, consumer-legible **access receipts**, a
**user-verifiable** (recompute-it-in-your-browser) audit log, a **portable,
consent-gated account alias**, and two clearly-labelled simulations of where open
finance is heading (selective-disclosure proofs and a verifiable-credential
wallet). See **[The consent frontier](#going-further--the-consent-frontier)**.

---

## Try it live

### ▶ **[cdb-aggregator.onrender.com](https://cdb-aggregator.onrender.com)**

The whole app — API **and** UI — runs as a single service on one public URL.

> **First load takes ~2–3 minutes.** It's on a free tier that sleeps when idle, so
> the first request has to wake and start the container (you'll see a "waking up"
> screen — give it a couple of minutes and refresh). Subsequent visits are instant
> until it idles again.

Continuous deployment is on: **every push to `main` redeploys the latest code**, so
the link always serves what's current — [`render.yaml`](render.yaml) +
[`Dockerfile`](Dockerfile) build the React app and serve it from FastAPI.

> Honest scope, same as everywhere else here: it's seeded with **demo data** and
> in-memory state (each visitor gets their own sandbox — there's a **Reset demo**
> button), there's no login. It demonstrates the architecture; it isn't a live
> integration with any real bank.

Prefer to run it yourself? One command with Docker, or the from-source
[Quickstart](#quickstart) below:

```bash
docker build -t cdb-aggregator . && docker run --rm -p 8000:8000 cdb-aggregator
# → http://localhost:8000  (UI, API at /api, docs at /docs)
```

---

## The regulatory moment

Canada's open-banking framework just moved from proposal to law:

- **Bill C-15 received Royal Assent on March 26, 2026**, replacing the original
  Consumer-Driven Banking Act with a comprehensive new **CDBA** and moving
  oversight to the **Bank of Canada**.
- **Phase 1 (read access)** was targeted for early 2026; **Phase 2 (write —
  payment initiation, account switching)** for mid-2027, contingent on Real-Time
  Rail. Timing is genuinely uncertain — this project is built *for* that world,
  it does not claim to be *in* it yet.
- The technical standard is **[FDX](https://financialdataexchange.org/)** —
  OAuth 2.0 + FAPI, granular time-limited permissions, and five principles:
  **Control, Access, Transparency, Traceability, Security.**

Most aggregation in Canada still runs on **screen-scraping and shared
credentials** — brittle, and far more access than any feature needs. This project
is built the other way around: FDX-first, with consent and an auditable access
trail as the core product. See **[docs/screen-scraping.md](docs/screen-scraping.md)**
for the full "why screen-scraping is about to break" argument.

### What it is — and isn't

- It **is** a working demonstration of the architecture open banking calls for:
  a canonical FDX model, adapters that normalize messy sources into it, and a
  consent layer that gates, logs, and minimizes every read.
- It is **not** a live integration with any real institution or regulator. The
  data sources are mocks; persistence is in-memory (see
  [ADR 0006](docs/adr/0006-in-memory-stores-and-mocks.md)). It models the
  standard rather than claiming certified connectivity.

---

## The star: consent & traceability

Every capability below is enforced at a **single choke point** — a consent gate
that all data reads pass through ([ADR 0003](docs/adr/0003-consent-as-a-gate.md)):

- **Granular scopes** — account details, balances, transactions, investment
  holdings, customer identity, customer contact — granted per connection.
- **Time-limited & revocable** — grants expire; one-tap revoke stops access
  immediately.
- **Enforced on every read** — no active, in-scope grant covering the account
  means no data, with a specific reason (`NO_CONSENT` / `INACTIVE` /
  `SCOPE_NOT_GRANTED` / `ACCOUNT_NOT_COVERED`).
- **Traceability** — an append-only audit log records every access (allowed *or*
  denied), tied to the grant it relied on, noting what was disclosed and what was
  withheld ([ADR 0004](docs/adr/0004-traceability-and-minimization.md)).
- **Data minimization** — a read returns only the fields the granted scopes
  permit; balances you didn't share drop out of net worth as *excluded*, not
  silently.
- **Agentic delegation** — a task delegated to an AI agent is just another consent
  to an agent identity: scoped, revocable, logged, and suggestion-only
  ([ADR 0005](docs/adr/0005-agentic-delegation-as-consent.md)).

---

## Going further — the consent frontier

The same consent + traceability thesis, extended onto the screen. Everything here
runs on the mock/in-memory stack; the last two are **clearly-labelled
simulations** — they demonstrate a pattern, not real infrastructure.

- **Agent activity & authority console** — the delegated agent as a visible,
  revocable object: a live action feed (each read tied to the grant that
  authorized it), an authority card (scope, time remaining, Pause / Revoke), an
  approval queue for its suggestion-only actions, and an intent → scope preview
  before you grant. Pausing or revoking halts the feed immediately.
- **Access receipts + permission simulation** — every audit entry re-rendered as
  a plain-language receipt (who, what, under which grant, disclosed vs withheld,
  with a JSON export), plus a "which fields would this scope share?" preview
  before you grant.
- **User-verifiable audit log** — the log is a SHA-256 hash chain; a **Verify
  integrity** control recomputes every link **in your browser** (Web Crypto) and
  reports intact / tampered, with a "download log + proof" export. Append-only you
  can check, not just append-only by assertion.
- **Portable, consent-gated alias** — a bank-neutral handle (`ada.cdb`) that
  resolves to a **one-time routing token**, never the raw institution / transit /
  account; resolution is consent-gated, re-pointing is a logged event, and every
  resolution lands in the trail.
- **Selective-disclosure attestation** *(simulated)* — prove a derived fact
  ("holds ≥ $10k in liquid assets") and share only the signed conclusion, never
  the balances. Signed with a demo key, not a real zero-knowledge proof.
- **Verifiable-credential wallet** *(simulated)* — hold those attestations and
  present a **selected** subset to a verifier that checks signatures against its
  policy — the OID4VP-style holder → verifier flow, on mock data.

---

## Architecture

```
  Mock FDX bank ─┐   (OAuth2 + FDX JSON)
  Legacy bank   ─┼─▶  Adapters / normalizer ─▶  Canonical FDX model
  OldBank (scrape)┘   (one per source)          (Account, Balance, Transaction,
                                                 InvestmentHolding, Customer, Consent)
                                                        │
                                                        ▼
                         ┌─────────────────────────────────────────────────┐
   React client  ◀─REST─ │  CONSENT + TRACEABILITY GATE                     │
   6 views, all          │  every read → active in-scope grant? → minimize  │
   through the gate      │  → append-only, hash-chained audit (who, what,   │
                         │     withheld) — verifiable in the browser        │
                         └─────────────────────────────────────────────────┘
                                                        ▲
                                    delegated agent (scoped, revocable, logged)
```

Three sources with three very different shapes normalize into one model; the gate
sits between that model and everything that consumes it — the dashboards and the
agent alike.

### Repository layout

```
cdb-aggregator/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app factory (CORS, routers, demo state)
│   │   ├── core/config.py      # typed settings
│   │   ├── models/             # canonical FDX model                    (Item 2)
│   │   ├── providers/          # mock FDX / legacy / scraped banks      (Items 3,4,6)
│   │   ├── adapters/           # normalizers: raw source → canonical    (Items 5,6)
│   │   ├── consent/            # store, gate, reader, audit, minimize   (Items 7,8)
│   │   ├── agent/              # idle-cash finder (delegated intent)     (Item 11)
│   │   ├── alias/              # portable, consent-gated alias resolver  (item-31)
│   │   ├── attestation.py      # selective-disclosure proofs (sim)       (item-32)
│   │   ├── verifier.py         # VC presentation / verifier (sim)        (item-33)
│   │   ├── comparison.py       # old-way vs new-way contrast            (Item 6)
│   │   └── api/                # HTTP API: consent, aggregation, agent,
│   │                           #  receipts, alias, attestations         (Items 9–11, 28–33)
│   └── tests/                  # pytest suite (100% coverage)
├── frontend/                   # React (Vite): 6 tabs — Overview, Consent &
│                               #  Traceability, Assistant, Old vs New,
│                               #  Portable address, Credentials
├── docs/
│   ├── adr/                    # architecture decision records
│   ├── screen-scraping.md      # "why screen-scraping is about to break"
│   ├── THREAT_MODEL.md         # trust boundaries, STRIDE, audit integrity
│   ├── fdx-conformance.md      # schema-validated FDX entities/fields
│   ├── project-review.md       # walkthrough script
│   ├── build-todo.md           # build roadmap (item-01 … item-14)
│   ├── polish-todo.md          # follow-on roadmap (item-15 … item-33)
│   └── research-report.md      # regulatory & standards context
├── Dockerfile                  # one image: build the UI, serve it + the API
├── render.yaml                 # Render blueprint — one-click, auto-deploying URL
└── .github/workflows/          # ci.yml (lint+tests+build) · tag-items.yml · retag.yml
```

---

## Quickstart

Requires **Python 3.11+** and **Node 20+**.

```bash
# 1. Install the backend (with dev tools)
pip install -e ".[dev]"

# 2. Run the aggregator API
uvicorn app.main:app --reload --app-dir backend      # http://127.0.0.1:8000
```

- <http://127.0.0.1:8000/docs> — interactive OpenAPI docs
- <http://127.0.0.1:8000/api/net-worth>, `/api/connections`, `/api/audit`, … — the
  dashboard API

### Run the dashboard

```bash
cd frontend && npm install && npm run dev            # http://localhost:5173
```

Six tabs, all reading through the consent gate:

- **Overview** — household net worth, merged accounts, merged transaction feed.
- **Consent & Traceability** — connections, scopes, expiry, one-tap revoke, the
  audit log (with *who* accessed — aggregator vs. delegated agent), the in-browser
  **chain verifier**, a **permission simulator**, and **access receipts**.
- **Assistant** — delegate a scoped, revocable task to the idle-cash agent, then
  the **authority console**: live action feed, Pause / Revoke, and an approval
  queue. It suggests, it never acts.
- **Old vs New** — a side-by-side contrast of credential screen-scraping and
  token-based FDX access.
- **Portable address** — a bank-neutral alias resolved to a one-time routing
  token, never your account; consent-gated, with a resolution history.
- **Credentials** *(simulation)* — prove a fact without sharing the data behind
  it, hold the signed attestation in a wallet, and present a selected subset to a
  verifier.

### Run it as one service (prod-style)

In dev the two run separately (Vite proxies `/api` to the backend). For a
single-process deploy, build the UI and point the API at it — then FastAPI
serves the SPA at `/` and the API under `/api` on one port. This is exactly what
the [Dockerfile](Dockerfile) and the [live deploy](#try-it-live) do.

```bash
cd frontend && npm install && npm run build && cd ..
CDB_FRONTEND_DIST="$PWD/frontend/dist" uvicorn app.main:app --app-dir backend
# → http://127.0.0.1:8000  (UI + API + /docs, one process)
```

### Run the mock providers (optional)

Each is a standalone service the adapters can talk to over HTTP:

```bash
uvicorn app.providers.mock_fdx_bank.app:app --app-dir backend --port 9001  # OAuth2 + FDX
uvicorn app.providers.legacy_bank.app:app   --app-dir backend --port 9002  # messy schema
uvicorn app.providers.scraper_bank.app:app  --app-dir backend --port 9003  # HTML to scrape
```

See each provider's `README.md` for endpoints and how it differs from FDX.

---

## Testing & CI

```bash
pytest                                               # the full suite
pytest --cov=app --cov-report=term-missing           # with coverage
```

- **100% line coverage**, enforced in CI (`--cov-fail-under=100`).
- **Warnings are errors** — nothing slips through silently in a financial
  codebase.
- **Property-based tests** (Hypothesis) assert the consent invariants across
  thousands of random inputs; **FDX schema conformance** validates the mock
  provider's responses so drift fails the build (see
  [docs/fdx-conformance.md](docs/fdx-conformance.md)).
- **[GitHub Actions](.github/workflows/ci.yml)** runs ruff (lint + format),
  the tests + coverage gate, and the frontend build on every push and PR.

Configuration is typed (`backend/app/core/config.py`); copy `.env.example` to
`.env` to override (all vars prefixed `CDB_`).

---

## Design decisions

The *why* behind the structure is recorded as **[ADRs](docs/adr/)**:

| # | Decision |
|---|----------|
| [0001](docs/adr/0001-backend-fastapi.md) | Backend: FastAPI (Python) |
| [0002](docs/adr/0002-fdx-aligned-canonical-model.md) | FDX-aligned model; `Decimal` money; camelCase wire format |
| [0003](docs/adr/0003-consent-as-a-gate.md) | Consent as a gate every read passes |
| [0004](docs/adr/0004-traceability-and-minimization.md) | Append-only audit + field-level minimization |
| [0005](docs/adr/0005-agentic-delegation-as-consent.md) | Agent delegation as a consent to an agent identity |
| [0006](docs/adr/0006-in-memory-stores-and-mocks.md) | In-memory stores + mock providers (SQLite behind the seam) |

## Security

The trust boundaries, threats/mitigations, audit-log integrity guarantees, and
the path to real FDX accreditation are written up in
**[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md)** — for a system whose product is
auditable consent, that reasoning is part of the build.

---

## Build timeline

Built in **Items** (see [`docs/build-todo.md`](docs/build-todo.md)), in
dependency order, each tagged so the history is a navigable timeline:

| Phase | Items | What lands |
|------:|-------|-----------|
| **0 — Foundation** | 1–2 | Repo scaffold; FDX-aligned canonical model |
| **1 — Ingestion** | 3–6 | Mock FDX bank; messy bank; normalizer; screen-scraping contrast |
| **2 — Consent ★** | 7–9 | Consent lifecycle + enforcement; audit + minimization; consent dashboard |
| **3 — Aggregation UX** | 10 | Unified accounts + household net-worth dashboard |
| **4 — Differentiator** | 11 | Agentic delegation / intent layer |
| **5 — Packaging** | 12–14 | Test hardening + CI; README + ADRs + explainer; project-review walkthrough |

A follow-on roadmap continues the timeline (see
[`docs/polish-todo.md`](docs/polish-todo.md)), same one-item-per-tag cadence:

| Track | Items | What lands |
|------:|-------|-----------|
| **UI refinement** | 15–21 | Design system, dark mode, log controls, states, minimization signature, screen-scraping visual, accessibility |
| **Hardening** | 22–27 | Hash-chained audit log, FAPI (PAR + PKCE), property-based tests, SQLite persistence, threat model, FDX schema conformance |
| **Consent frontier** | 28–33 | Agent authority console; portable alias; user-verifiable audit log; access receipts + permission simulation; selective-disclosure + VC wallet *(simulated)* |

```bash
git tag                      # item-01 … item-33
git checkout item-07         # inspect any milestone (e.g. the consent layer)
```

---

## Trade-offs & honest scope

- **Mock sources, in-memory persistence.** Deliberate — it demonstrates the
  architecture without an external dependency, and the store interfaces are the
  seam where a database drops in ([ADR 0006](docs/adr/0006-in-memory-stores-and-mocks.md)).
- **FDX-aligned, not FDX-complete.** A faithful, pragmatic subset of the spec.
- **The agent is deterministic by default.** The differentiator is the
  *governance* around a delegated actor, not the AI; the engine is swappable for
  an LLM without changing any of it ([ADR 0005](docs/adr/0005-agentic-delegation-as-consent.md)).
- **Built for the standard, honest about timing.** No claim of certified
  connectivity that doesn't exist yet.

## Tech stack

- **Backend:** Python 3.11, FastAPI, Pydantic v2, httpx, BeautifulSoup
- **Frontend:** React 18 + Vite
- **Tooling:** pytest (+ coverage), ruff, GitHub Actions
