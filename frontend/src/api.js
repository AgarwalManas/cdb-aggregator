// Thin client for the consent dashboard API (see backend app/api/routes/consent.py).
// Uses relative /api URLs; the Vite dev server proxies them to the backend.

const BASE = "/api";

async function request(path, options) {
  const res = await fetch(BASE + path, options);
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

export const revokeConnection = (connectionId) =>
  request(`/connections/${connectionId}/revoke`, { method: "POST" });

export const grantConnection = (body) =>
  request("/connections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
