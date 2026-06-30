# Frontend (placeholder)

This directory is reserved for the **React** client. It is intentionally empty
at the scaffold stage.

It gets populated later in the build:

- **Item 9 — Consent dashboard (React):** list connections, show scopes +
  expiry, one-tap revoke, and a view of the traceability audit log. This is the
  screen demoed first.
- **Item 10 — Unified accounts + net-worth dashboard (React):** merged accounts,
  merged transaction feed, and a household net-worth view. Every read flows
  through the consent gate built in Phase 2.

The client will talk to the FastAPI backend in `../backend` over REST. When it's
time to build it, this becomes a standard React app (Vite) and the root
`.gitignore` already covers `node_modules/`, `dist/`, and `build/`.
