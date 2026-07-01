# Build To-Do: FDX-First Consumer-Driven Banking Aggregator

A portfolio project to demonstrate Wealthsimple-relevant skills and judgment. The standout feature is a **first-class consent + traceability layer** (the thing that separates an accredited open-banking provider from a screen scraper), built on an **FDX-aligned data model**, plus **one differentiator**.

## How to use this list
- Do **one item per chat** to keep context small. Each item below has a ready-to-paste **kickoff prompt**.
- Start each new chat by pasting that item's kickoff prompt. It tells me to pull the prior work from this project's history before building, so context reloads automatically.
- Items are ordered by dependency. Don't skip ahead past a "depends on" without the earlier piece existing.
- Check items off here as you finish them.

## One decision to make before Item 1
**Backend language.** Pick one and tell me in Item 1's chat:
- **Ruby on Rails** — most on-brand (≈half of Wealthsimple's services are Rails); strongest "could drop into our codebase" signal.
- **Python (FastAPI)** — fastest to build, cleanest for the data/normalizer work.
- **Node/Express** — pick if JavaScript is your strongest language and you want one language across the stack.

Frontend is **React** either way (their frontend is React/React Native).

---

## Phase 0 — Foundation

### [x] Item 1 — Repo scaffold + backend decision
**Produces:** a runnable skeleton repo (backend + `frontend/` placeholder), folder structure, dependency/config setup, a README stub with the CDBA/FDX framing up top, `.gitignore`, and a "hello world" health-check endpoint that runs locally.
**Depends on:** nothing.
**Kickoff prompt:**
> New chat for my Wealthsimple open-banking project. Pull the build to-do list and research report from this project's history first. I'm starting **Item 1 — repo scaffold**. My backend choice is: **[Rails / FastAPI / Node]**. Scaffold the full repo skeleton, runnable locally, with a README stub framed around Consumer-Driven Banking + FDX.

### [x] Item 2 — FDX-aligned canonical data model
**Produces:** the core domain types modeled on the FDX data model — `Account`, `Balance`, `Transaction`, `InvestmentHolding`, `Customer`, and `Consent` — with field validation and unit tests. This is the schema everything else maps into.
**Depends on:** Item 1.
**Kickoff prompt:**
> Wealthsimple project, **Item 2 — FDX-aligned canonical data model**. Pull the to-do list and Item 1's scaffold from this project's history. Build the canonical types (Account, Balance, Transaction, InvestmentHolding, Customer, Consent) modeled on FDX, with validation and unit tests.

---

## Phase 1 — Data ingestion & normalization

### [x] Item 3 — Mock FDX-compliant data provider #1
**Produces:** a small standalone mock "bank" server that returns **FDX-shaped JSON** and issues mock OAuth2 access tokens (token endpoint + a couple of protected resource endpoints). This is your clean, API-first, standards-native source.
**Depends on:** Item 2.
**Kickoff prompt:**
> Wealthsimple project, **Item 3 — mock FDX-compliant data provider**. Pull the to-do list and the canonical model (Item 2) from this project's history. Build a mock bank server returning FDX-shaped JSON with a mock OAuth2 token flow.

### [x] Item 4 — Mock bank source #2 (messy schema)
**Produces:** a second mock source with a **deliberately different / messy schema** (different field names, date formats, nested vs flat). Its purpose is to prove the normalizer can tame real-world inconsistency.
**Depends on:** Item 2 (and conceptually Item 3 for contrast).
**Kickoff prompt:**
> Wealthsimple project, **Item 4 — second mock bank with a messy schema**. Pull the to-do list, canonical model, and Item 3 from this project's history. Build a second mock source whose schema deliberately differs from FDX so the normalizer has something hard to map.

### [x] Item 5 — Normalizer / adapter layer
**Produces:** an adapter per source that maps raw source data → the canonical FDX model, behind a common interface, with **per-adapter tests** (Wealthsimple values automated tests, so this item carries weight).
**Depends on:** Items 2, 3, 4.
**Kickoff prompt:**
> Wealthsimple project, **Item 5 — normalizer/adapter layer**. Pull the to-do list, canonical model, and both mock sources (Items 3–4) from this project's history. Build one adapter per source mapping into the canonical model, with per-adapter tests.

### [x] Item 6 — (Stretch) Screen-scraping mock + "old way vs new way"
**Produces:** a fake HTML statement page parsed by a scraper adapter, plus a toggle/comparison that dramatizes credential-based scraping vs token-based FDX access. Directly echoes the screen-scraping pain Wealthsimple has publicly documented.
**Depends on:** Item 5.
**Kickoff prompt:**
> Wealthsimple project, **Item 6 — screen-scraping mock + old-way/new-way comparison**. Pull the to-do list and the normalizer (Item 5) from this project's history. Add a fragile screen-scraping source and a comparison that contrasts it with the FDX token approach.

---

## Phase 2 — The star: consent & traceability

### [x] Item 7 — Consent model + enforcement
**Produces:** the `Consent` lifecycle — granular **scopes**, **expiry**, **grant/revoke** — plus enforcement middleware so **every data read checks an active, in-scope consent** before returning anything. Tests for the enforcement path.
**Depends on:** Items 2, 5.
**Kickoff prompt:**
> Wealthsimple project, **Item 7 — consent model + enforcement**. Pull the to-do list, canonical model, and normalizer from this project's history. Build the consent lifecycle (scopes, expiry, grant/revoke) and middleware that gates every read on an active in-scope consent, with tests.

### [x] Item 8 — Traceability audit log + data minimization
**Produces:** an **append-only audit log** recording every data access tied to its consent grant, plus **data-minimization** enforcement (a read returns only the fields the granted scope permits). Maps to FDX's Traceability + Control principles.
**Depends on:** Item 7.
**Kickoff prompt:**
> Wealthsimple project, **Item 8 — traceability audit log + data minimization**. Pull the to-do list and the consent layer (Item 7) from this project's history. Add an append-only access log tied to consent grants, and enforce field-level data minimization per scope.

### [x] Item 9 — Consent dashboard UI (React)
**Produces:** the React UI for the consent layer — list connections, show scopes + expiry, **one-tap revoke**, and a view of the audit log. This is the screen you'll demo first; make it clean.
**Depends on:** Items 7, 8.
**Kickoff prompt:**
> Wealthsimple project, **Item 9 — consent dashboard UI in React**. Pull the to-do list and the consent + audit-log work (Items 7–8) from this project's history. Build the React consent dashboard: connections, scopes, expiry, one-tap revoke, audit-log view.

---

## Phase 3 — Aggregation UX

### [x] Item 10 — Unified accounts + net-worth dashboard (React)
**Produces:** the main client view — merged accounts list, merged transaction feed, and a **household net-worth view** echoing "Wealthsimple Households." All reads flow through the consent gate from Phase 2.
**Depends on:** Items 5, 7, 9.
**Kickoff prompt:**
> Wealthsimple project, **Item 10 — unified accounts + net-worth dashboard**. Pull the to-do list, normalizer, and consent layer from this project's history. Build the React dashboard: merged accounts, merged transactions, household net-worth view — all reads gated by consent.

---

## Phase 4 — Differentiator (pick ONE)

### [x] Item 11 — Differentiator (chose A — agentic delegation / intent layer)
**Produces:** one standout capability. Choose based on where Wealthsimple is heading:
- **A — Agentic delegation / intent layer:** delegate a scoped, revocable, fully logged task to an AI agent (e.g., "find idle cash earning under 1% and suggest a move"). Lands on FDX's 2026 agentic-AI themes and the "intelligent assistant in the background" vision. *Highest-upside, least commoditized.*
- **B — Household aggregation deepening:** richer multi-member net-worth, shared goals, surplus insights. *Safest; mirrors a feature they just shipped.*
- **C — Fee-leak / investment-surplus detector:** analyze aggregated transactions to surface wasted fees and investable idle cash. *Echoes their spend-insights roadmap and low-fee gospel.*
**Depends on:** Item 10.
**Kickoff prompt:**
> Wealthsimple project, **Item 11 — differentiator, option [A/B/C]**. Pull the to-do list, dashboard, and consent layer from this project's history. Build differentiator option [A/B/C] on top of the existing aggregator, keeping every data access consent-gated and logged.

---

## Phase 5 — Packaging (this is what gets you the interview)

### [ ] Item 12 — Test hardening + CI
**Produces:** broadened automated test coverage across adapters, consent enforcement, and data minimization, plus a **GitHub Actions** CI workflow that runs them. Demonstrates the "ship daily with automated tests" engineering culture.
**Depends on:** Items 5, 7, 8 (more coverage = better).
**Kickoff prompt:**
> Wealthsimple project, **Item 12 — test hardening + GitHub Actions CI**. Pull the to-do list and the current codebase summary from this project's history. Broaden tests across adapters/consent/data-minimization and add a CI workflow.

### [ ] Item 13 — README, ADRs, and the screen-scraping writeup
**Produces:** a polished README framed around the client and the regulatory moment (CDBA dates, FDX, the consent architecture, trade-offs); a few short **architecture decision records**; and a standalone "why screen-scraping is about to break" explainer.
**Depends on:** most build items done.
**Kickoff prompt:**
> Wealthsimple project, **Item 13 — README + ADRs + screen-scraping writeup**. Pull the to-do list, research report, and project structure from this project's history. Write the polished README, a few ADRs, and the screen-scraping-vs-FDX explainer.

### [ ] Item 14 — "Project Review" walkthrough + post draft
**Produces:** a tight script for the **30-minute Project Review** (an actual stage in Wealthsimple's engineering interview) — problem, architecture, the consent layer, trade-offs, what you'd do for real accreditation — plus a short LinkedIn/blog post draft to share the project publicly.
**Depends on:** Item 13.
**Kickoff prompt:**
> Wealthsimple project, **Item 14 — Project Review walkthrough + post draft**. Pull the to-do list, README, and research report from this project's history. Write a 30-minute project-review script and a short LinkedIn/blog post draft.

---

## Quick reference — dependency order
1 → 2 → (3, 4) → 5 → [6 optional] → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14

## Notes to keep in mind
- Build **FDX-first** but don't claim live regulatory integration — Phase-1 read access had no firm Bank of Canada date as of early 2026.
- The **consent + traceability layer is the differentiator that signals judgment** — give it the most polish.
- Mirror their engineering values in the artifact itself: keep it simple, write clean human- and AI-friendly code, real tests, document decisions like an owner. Building with AI tooling is an explicit expectation there — using it is fine to mention.
