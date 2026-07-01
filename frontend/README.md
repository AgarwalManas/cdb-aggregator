# Frontend — Dashboard (Items 9-10)

The **React** client, with two tabs:

- **Overview** (Item 10): household **net worth**, **merged accounts** across every
  connected source, and a **merged transaction feed**. Every figure is read
  through the consent gate — a balance you didn't share (or a connection you
  revoked) simply isn't counted.
- **Consent & Traceability** (Item 9): list connections, see each one's scopes +
  expiry, **one-tap revoke**, connect a new source with only the scopes you
  choose, and read the **traceability log** of every access (allowed or denied).

Built with **Vite + React**. It talks to the FastAPI backend over the consent +
aggregation API (`/api/...`, see `backend/app/api/routes/`).

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

## What it shows

Backend seed data (`backend/app/api/demo.py`) sets up a customer with three
connections — the mock FDX bank, the messy legacy bank, and the screen-scraping
"OldBank" — each scoped to that source's accounts and spanning assets and
liabilities. The scraped connection is granted `ACCOUNT_DETAILS` + `TRANSACTIONS`
but **not** `BALANCES`, so its mortgage balance is withheld and drops out of net
worth — consent visibly deciding what you see. A real audit trail (including a
**denied** read) is produced by running reads through the Item 7/8 enforcing
reader.

## Structure

```
src/
  App.jsx                 tabbed shell (Overview / Consent) + scope catalog
  api.js                  fetch client for /api
  format.js               date / money / expiry helpers
  pages/
    OverviewPage.jsx      net worth + accounts + transactions (Item 10)
    ConsentPage.jsx       connections + revoke + audit log (Item 9)
  components/
    NetWorthPanel.jsx     household net-worth hero
    AccountsList.jsx      merged accounts grouped by source
    TransactionsFeed.jsx  merged transaction feed
    ConnectionCard.jsx    a connection: status, scopes, expiry, revoke
    ConnectForm.jsx       grant a new connection with chosen scopes
    AuditTable.jsx        the traceability log
    ScopeChip.jsx         a scope pill (human label from /api/scopes)
  styles.css
```

Later (Item 10) this app gains the unified accounts + net-worth dashboard; every
read there flows through the same consent gate shown here. The root `.gitignore`
already covers `node_modules/`, `dist/`, and `build/`.
