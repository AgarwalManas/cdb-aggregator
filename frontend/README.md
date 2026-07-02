# Frontend — Dashboard

The **React** (Vite) client. A left **sidebar shell** with grouped navigation and
nine pages — every figure read through the consent gate, so a balance you didn't
share, or a connection you revoked, simply isn't counted. The sidebar collapses
to an icon rail and has a page search in its header; a top bar carries the page
title, a **Demo data** pill, **Reset demo**, and the light/dark toggle.

The nav is grouped into the product, a clearly-quarantined demo frontier, and the
explainers:

**Product**

- **Dashboard** — the at-a-glance overview: active connections, data categories
  shared, access counts, your portable address, recent activity, a monochrome
  "data you've shared" breakdown, connected sources, net worth, and log
  integrity — each tile deep-linking into the page that owns it.
- **Bank Accounts** — household **net worth**, **merged accounts** across every
  connected source, and a **merged transaction feed**, with withheld balances
  shown as explicitly excluded rather than silently dropped.
- **Control Centre** — two sub-tabs. **Connectors** lists each source (with a
  bank tile), its scopes + expiry, **one-tap revoke**, an expandable preview of
  exactly what it can access, a connect-a-source form, and a **permission
  simulator**. **Activity Logs** is the merged audit + receipts table — filter by
  date / field, search, tick-to-export (Markdown / CSV / JSON / PDF), and expand
  any row into a **plain-language receipt** (who read what, for which account,
  under which grant, what they saw vs kept private). The compact **chain
  verifier** sits on the sub-tab row.
- **Assistant** — two sub-tabs. **Chat** is a single, persistent conversation
  where you ask about your money, delegate, and approve/reject inline; it's a
  **scripted demo (no LLM)**, answering from your consent-gated data, and it
  carries a visible **context budget** that compresses older turns past a token
  limit. **Activity** is the authority console: an authority card (scope, time
  remaining, Pause / Revoke), a live action feed, and an approval queue. It
  **suggests, never acts**, and every access is logged against the agent.

**Explore (Demo)**

- **Portable Address** — a bank-neutral alias (`ada.cdb`) resolved to a
  **one-time routing token**, never your account; consent-gated, with a
  resolve-as-a-counterparty flow and a resolution history.
- **Credentials** *(simulation)* — prove a fact without sharing the data behind
  it, hold the signed attestation in a wallet, and present a selected subset to a
  verifier.

**Trust & Privacy**

- **How it works** — the six-step journey through the product, each step
  deep-linking into the feature that does it.
- **Why this is safer** — the case for scoped, revocable, token-based access.
- **Old vs New** — a side-by-side contrast of credential screen-scraping and
  token-based FDX access, plus the principles behind the new model.

Built with **Vite + React 18**, a dependency-free inline-SVG icon set, self-hosted
variable fonts (no CDN), and a light/dark theme. It talks to the FastAPI backend
over the `/api` surface (see `backend/app/api/routes/`), same-origin so the
per-visitor session cookie rides along.

## Run it

The dashboard needs the backend running. In one terminal:

```bash
# from the repo root
uvicorn app.main:app --reload --app-dir backend        # serves /api on :8000
```

In another:

```bash
cd frontend
npm install
npm run dev                                            # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so there's no CORS
to worry about in development. Open <http://localhost:5173>.

```bash
npm run build      # production build to dist/
npm run preview    # preview the production build
```

For a single-process deploy, the backend serves this build directly — see the
root README's "Run it as one service" section and the `Dockerfile`.

## What it shows

Backend seed data (`backend/app/api/demo.py`) sets up a customer with three
connections — the mock FDX bank, the messy legacy bank, and the screen-scraping
"OldBank" — each scoped to that source's accounts and spanning assets and
liabilities. The scraped connection is granted `ACCOUNT_DETAILS` + `TRANSACTIONS`
but **not** `BALANCES`, so its mortgage balance is withheld and drops out of net
worth — consent visibly deciding what you see. A real audit trail (including a
**denied** read) is produced by running reads through the consent-enforcing
reader.

## Structure

```
src/
  App.jsx        the sidebar shell (grouped nav, top bar) + page routing + scope catalog
  api.js         fetch client for /api (same-origin, credentialed)
  format.js      date / money / percent / expiry helpers
  theme.js       light/dark theme handling
  pages/         one component per page:
                   DashboardPage, OverviewPage (Bank Accounts),
                   ConsentPage (Control Centre), AgentPage (Assistant),
                   AddressPage, CredentialsPage,
                   HowItWorksPage, WhySaferPage, ComparePage (Old vs New)
  components/    shared building blocks, grouped by area:
                   Sidebar, Icon, HowItWorksStrip (shell + cross-cutting);
                   NetWorthPanel, AccountsList, TransactionsFeed (Bank Accounts);
                   ConnectionCard, ConnectForm, ActivityLog, ChainVerifier,
                   PermissionSimulator (Control Centre);
                   AssistantChat, AuthorityCard, ActivityFeed, ApprovalQueue,
                   AssistantSuggestion, ScopePreview (Assistant);
                   ScopeChip, ConfirmButton, Skeleton, Toaster,
                   ThemeToggle (cross-cutting)
  styles.css     the design tokens (2 neutrals + 1 accent) and component styles
```

Every read across every page flows through the same consent gate. The root
`.gitignore` covers `node_modules/`, `dist/`, and `build/`.
