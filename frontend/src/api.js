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
export const getAuditVerify = () => request("/audit/verify"); // hash-chain integrity (item-22)

// Old-way vs new-way contrast (item-20)
export const getComparison = () => request("/comparison");

// Aggregation (Item 10)
export const getAccounts = () => request("/accounts");
export const getTransactions = () => request("/transactions");
export const getNetWorth = () => request("/net-worth");

// Agentic delegation (Item 11)
export const getDelegation = () => request("/agent/delegation");
export const delegateAgent = () => request("/agent/delegation", { method: "POST" });
export const revokeDelegation = () => request("/agent/delegation/revoke", { method: "POST" });
export const runAgent = () => request("/agent/run", { method: "POST" });

// Agent activity & authority console (item-28)
export const getAuthority = () => request("/agent/authority");
export const getActivity = () => request("/agent/activity");
export const getScopePreview = () => request("/agent/preview");
export const getApprovals = () => request("/agent/approvals");
export const pauseAgent = () => request("/agent/pause", { method: "POST" });
export const resumeAgent = () => request("/agent/resume", { method: "POST" });
export const decideApproval = (approvalId, body) =>
  request(`/agent/approvals/${approvalId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const revokeConnection = (connectionId) =>
  request(`/connections/${connectionId}/revoke`, { method: "POST" });

export const grantConnection = (body) =>
  request("/connections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

// Portable alias + consent-gated resolver (item-31)
export const getAlias = () => request("/alias");
export const resolveAlias = (body) =>
  request("/alias/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
export const exchangeToken = (token) =>
  request("/alias/exchange", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
export const repointAlias = (accountId) =>
  request("/alias/repoint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accountId }),
  });

// Reset this visitor's demo world back to its seeded state (Item: deploy demo).
export const resetDemo = () => request("/demo/reset", { method: "POST" });
