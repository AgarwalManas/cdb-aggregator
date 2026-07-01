// Thin client for the consent dashboard API (see backend app/api/routes/consent.py).
// Uses relative /api URLs; the Vite dev server proxies them to the backend.

const BASE = "/api";

async function request(path, options) {
  // Same-origin so the per-session cookie (which world is "yours") rides along.
  const res = await fetch(BASE + path, { credentials: "same-origin", ...options });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.status === 204 ? null : res.json();
}

export const getScopes = () => request("/scopes");
export const getSources = () => request("/sources");
export const getConnections = () => request("/connections");
export const getAudit = () => request("/audit");

// Aggregation (Item 10)
export const getAccounts = () => request("/accounts");
export const getTransactions = () => request("/transactions");
export const getNetWorth = () => request("/net-worth");

// Agentic delegation (Item 11)
export const getDelegation = () => request("/agent/delegation");
export const delegateAgent = () => request("/agent/delegation", { method: "POST" });
export const revokeDelegation = () => request("/agent/delegation/revoke", { method: "POST" });
export const runAgent = () => request("/agent/run", { method: "POST" });

export const revokeConnection = (connectionId) =>
  request(`/connections/${connectionId}/revoke`, { method: "POST" });

export const grantConnection = (body) =>
  request("/connections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

// Reset this visitor's demo world back to its seeded state (Item: deploy demo).
export const resetDemo = () => request("/demo/reset", { method: "POST" });
