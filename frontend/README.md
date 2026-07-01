# Frontend — Consent Dashboard (Item 9)

The **React** client for the consent + traceability layer. The screen you demo
first: list connections, see exactly which scopes each one shares and when it
expires, **one-tap revoke**, connect a new source with only the scopes you
choose, and read the **traceability log** of every access (allowed or denied).

Built with **Vite + React**. It talks to the FastAPI backend over the consent
API (`/api/...`, see `backend/app/api/routes/consent.py`).

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
"OldBank" — each scoped to that source's accounts, plus a real audit trail
produced by running reads through the Item 7/8 enforcing reader (including one
**denied** read, so the log shows an honest mix).

## Structure

```
src/
  App.jsx                 dashboard shell + data loading
  api.js                  fetch client for /api
  format.js               date / expiry helpers
  components/
    ConnectionCard.jsx    a connection: status, scopes, expiry, revoke
    ConnectForm.jsx       grant a new connection with chosen scopes
    AuditTable.jsx        the traceability log
    ScopeChip.jsx         a scope pill (human label from /api/scopes)
  styles.css
```

Later (Item 10) this app gains the unified accounts + net-worth dashboard; every
read there flows through the same consent gate shown here. The root `.gitignore`
already covers `node_modules/`, `dist/`, and `build/`.
