// Small presentation helpers shared across components.

export function formatDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// Human "expires in N days" / "expired" for a connection.
export function expiryLabel(connection) {
  if (connection.status === "REVOKED") {
    return `Revoked ${formatDate(connection.revokedAt)}`;
  }
  const now = Date.now();
  const expires = new Date(connection.expiresAt).getTime();
  const days = Math.ceil((expires - now) / (1000 * 60 * 60 * 24));
  if (days <= 0) return `Expired ${formatDate(connection.expiresAt)}`;
  if (days === 1) return "Expires tomorrow";
  return `Expires in ${days} days`;
}
