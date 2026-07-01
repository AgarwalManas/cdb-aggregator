# Frontend — Dashboard

The **React** (Vite) client. Six tabs, every figure read through the consent gate
— a balance you didn't share, or a connection you revoked, simply isn't counted.

- **Overview** — household **net worth**, **merged accounts** across every
  connected source, and a **merged transaction feed**, with withheld balances
  shown as explicitly excluded rather than silently dropped.
- **Consent & Traceability** — list connections, see each one's scopes + expiry,
  **one-tap revoke**, connect a new source with only the scopes you choose, and
  read the **traceability log** of every access (allowed or denied, and *who*
  accessed — the aggregator or a delegated agent). Includes the in-browser
  **chain verifier**, a **permission simulator**, and **access receipts**.
- **Assistant** — delegate a **scoped, revocable** task to the "Idle-Cash Finder";
  it returns a **suggestion, never an action**, and every access is logged against
  the agent. The **authority console** adds a live action feed, a Pause / Revoke
  card, and an approval queue.
- **Old vs New** — a side-by-side contrast of credential screen-scraping and
  token-based FDX access.
- **Portable address** — a bank-neutral alias resolved to a **one-time routing
  token**, never your account; consent-gated, with a resolution history.
- **Credentials** *(simulation)* — prove a fact without sharing the data behind
  it, hold the signed attestation in a wallet, and present a selected subset to a
  verifier.

Built with **Vite + React 18**, self-hosted variable fonts (no CDN), and a
light/dark theme. It talks to the FastAPI backend over the `/api` surface (see
`backend/app/api/routes/`), same-origin so the per-visitor session cookie rides
along.

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
  App.jsx        tabbed shell (nav + the six tabs) + scope catalog
  api.js         fetch client for /api (same-origin, credentialed)
  format.js      date / money / percent / expiry helpers
  theme.js       light/dark theme handling
  pages/         one component per tab:
                   OverviewPage, ConsentPage, AgentPage,
                   ComparePage, AddressPage, CredentialsPage
  components/    shared building blocks, grouped by area:
                   net worth / accounts / transactions (Overview);
                   connections, ConnectForm, AuditTable, ChainVerifier,
                   PermissionSimulator, ReceiptList (Consent);
                   AuthorityCard, ActivityFeed, ApprovalQueue,
                   AssistantSuggestion (Assistant);
                   ScopeChip, ConfirmButton, Skeleton, Toaster,
                   ThemeToggle (cross-cutting)
  styles.css     the design tokens (2 neutrals + 1 accent) and component styles
```

Every read across every tab flows through the same consent gate. The root
`.gitignore` covers `node_modules/`, `dist/`, and `build/`.
