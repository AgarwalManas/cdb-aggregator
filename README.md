# Consumer-Driven Banking Aggregator

[![CI](https://github.com/AgarwalManas/cdb-aggregator/actions/workflows/ci.yml/badge.svg)](https://github.com/AgarwalManas/cdb-aggregator/actions/workflows/ci.yml)

An **FDX-aligned account aggregator** for Canada's Consumer-Driven Banking era,
built around a **first-class consent and traceability layer** — the part that
separates an accredited open-banking participant from a credential-storing
screen scraper.

> **Status:** phased build in progress. The canonical model, three mock
> providers (FDX / messy / screen-scraped), the normalizer, the consent +
> traceability engine, both React dashboards, and an agentic-delegation layer are
> in; CI runs lint + tests (100% coverage, warnings-as-errors) + the frontend
> build on every push.
> See [Roadmap](#roadmap). A full rewrite lands in Item 13.

---

## Why this exists

Canada's **Consumer-Driven Banking Act (CDBA)** establishes a consumer's right
to direct their own financial data — securely, with consent, and without handing
over banking credentials. The **Financial Data Exchange (FDX)** standard is the
emerging North American technical expression of that right: token-based access
(OAuth 2.0 / FAPI), granular and time-limited permissions, and five core
principles — **Control, Access, Transparency, Traceability, Security**.

Today, most account aggregation in Canada still leans on **screen scraping** and
shared credentials. That approach is brittle (it breaks when a bank changes its
login page) and it asks users to surrender far more access than any single
feature needs. This project is built the other way around: **FDX-first**, with
consent and an auditable access trail treated as the core product, not an
afterthought.

### What this is — and isn't

- It **is** a working demonstration of the *architecture* open banking calls for:
  a canonical FDX-shaped data model, source adapters that normalize messy real-world
  data into it, and a consent layer that gates and logs every read.
- It is **not** a live integration with any real financial institution or
  regulator. Canada's Phase-1 (read access) had no firm Bank of Canada launch
  date as of early 2026, so this models the standard rather than claiming
  certified connectivity. The mock data providers are deliberately stand-ins for
  FDX-compliant banks.

---

## Architecture (target)

The data flow this scaffold is built to grow into:

```
  Mock FDX bank ─┐
                 ├─▶  Adapters / normalizer ─▶  Canonical FDX model ─┐
  Messy bank   ──┘     (one per source)         (Account, Balance,    │
                                                 Transaction, ...)     │
                                                                       ▼
                                            ┌───────────────────────────────────┐
   React client  ◀── REST ──  FastAPI  ◀──  │  CONSENT + TRACEABILITY GATE       │
   (dashboards)                             │  every read checks an active,      │
                                            │  in-scope grant, then writes an    │
                                            │  append-only audit entry           │
                                            └───────────────────────────────────┘
```

Every data read passes through the consent gate. No active, in-scope grant means
no data — and each read that *is* allowed leaves a traceable record.

### Repository layout

```
cdb-aggregator/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app factory + entry point
│   │   ├── core/             # config (typed settings), cross-cutting concerns
│   │   ├── api/routes/       # HTTP endpoints (health now; more per phase)
│   │   ├── models/           # canonical FDX data model            (Item 2)
│   │   ├── providers/        # mock FDX bank + messy-schema bank    (Items 3-4)
│   │   ├── adapters/         # normalizers: raw source -> canonical (Item 5)
│   │   └── consent/          # consent lifecycle + audit log        (Items 7-8)
│   └── tests/                # pytest suite
├── frontend/                 # React client placeholder             (Items 9-10)
├── pyproject.toml
├── .env.example
└── README.md
```

The empty package folders are intentional: each has a docstring describing the
phase that fills it, so the structure documents the plan.

---

## Quickstart

Requires **Python 3.11+**.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install the project (with dev tools)
pip install -e ".[dev]"

# 3. Run the API
uvicorn app.main:app --reload --app-dir backend
```

Then visit:

- <http://127.0.0.1:8000/health> — liveness probe
- <http://127.0.0.1:8000/docs> — interactive OpenAPI docs

### Run the mock FDX bank (Item 3)

A standalone mock data provider that issues OAuth2 tokens and serves FDX-shaped
JSON — the clean, standards-native source the normalizer will consume. Run it in
a separate terminal:

```bash
uvicorn app.providers.mock_fdx_bank.app:app --app-dir backend --port 9001
```

Then exchange client credentials for a token and call a protected endpoint:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:9001/oauth2/token \
  -d grant_type=client_credentials \
  -d client_id=cdb-aggregator -d client_secret=local-mock-secret \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:9001/fdx/v6/accounts
```

See `backend/app/providers/mock_fdx_bank/README.md` for the full endpoint list.

### Run the legacy bank (Item 4)

A second mock source with a deliberately **messy, non-FDX schema** (session auth,
one nested blob, abbreviated fields, signed amounts, mixed date formats) — the
hard case that justifies the normalizer:

```bash
uvicorn app.providers.legacy_bank.app:app --app-dir backend --port 9002
```

See `backend/app/providers/legacy_bank/README.md` for how it differs from FDX.

### Run the screen-scraping mock (Item 6, stretch)

A mock bank *website* (login form + HTML statement, no API) that dramatizes the
"old way" — credential sharing and fragile HTML parsing — versus token-based FDX
access:

```bash
uvicorn app.providers.scraper_bank.app:app --app-dir backend --port 9003
```

The scraper adapter (`app.adapters.scraper_bank`) parses its HTML into the same
canonical model; the structured contrast is in `app.comparison`. See
`backend/app/providers/scraper_bank/README.md`.

### Run the dashboard (Items 9-10)

The React client — two tabs: an **Overview** (household net worth, merged
accounts, merged transaction feed) and **Consent & Traceability** (connections,
scopes, expiry, one-tap revoke, audit log). Every figure is read through the
consent gate. With the API running (step 3 above), start the client in another
terminal:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to the backend)
```

See `frontend/README.md`.

### Run the tests

```bash
pytest
```

### Configuration

Copy `.env.example` to `.env` to override defaults (all variables are prefixed
`CDB_`). Settings are typed and centralized in `backend/app/core/config.py`.

---

## Roadmap

The build proceeds in dependency order. The consent + traceability layer is the
centerpiece and gets the most polish.

| Phase | Items | What lands |
|------:|-------|-----------|
| **0 — Foundation** | 1–2 | Repo scaffold *(this)*; FDX-aligned canonical data model |
| **1 — Ingestion** | 3–6 | Mock FDX bank; messy-schema bank; normalizer/adapter layer; (stretch) screen-scraping contrast |
| **2 — Consent ★** | 7–9 | Consent lifecycle + enforcement; traceability audit log + data minimization; React consent dashboard |
| **3 — Aggregation UX** | 10 | Unified accounts + household net-worth dashboard |
| **4 — Differentiator** | 11 | One standout capability (agentic delegation / household / fee-leak) |
| **5 — Packaging** | 12–14 | Test hardening + CI; full README + ADRs + screen-scraping writeup; project-review walkthrough |

---

## How this repo is built

The project is built in **Items** (see [`docs/build-todo.md`](docs/build-todo.md)),
one per work session, in dependency order. History is kept legible:

- Each Item lands as a commit (or a few) prefixed `Item NN — …`.
- Each completed Item is tagged `item-NN`, so the build can be walked as a
  timeline. To see a phase in isolation: `git checkout item-07` for the consent
  layer, for example.

```bash
git log --oneline            # the build, step by step
git tag                      # item-01, item-02, ...
git checkout item-07         # inspect any milestone
```

## Design principles

- **Keep it simple, make it obvious.** Small, typed, well-named modules; the
  folder structure mirrors the data flow.
- **Consent is not a feature, it's the gate.** Reads are designed to be
  impossible without an active, in-scope grant — and to be traceable when they happen.
- **Real tests, from the start.** Even the scaffold ships with a passing suite;
  coverage grows with each phase.
- **FDX-first, honest about scope.** Built to the standard, without claiming
  regulatory certification that doesn't exist yet.
- **Built with AI tooling, reviewed like an owner.** AI changes the *how*, not
  the *why*; the decisions and trade-offs are documented as the build proceeds.

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, pydantic-settings
- **Frontend:** React *(added in Phase 2)*
- **Tooling:** pytest, ruff, GitHub Actions CI *(added in Phase 5)*
