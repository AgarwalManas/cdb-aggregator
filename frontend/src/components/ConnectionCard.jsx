import { expiryLabel } from "../format.js";
import ScopeChip from "./ScopeChip.jsx";

// One connected data source: its status, the scopes it can see, when it expires,
// and one-tap revoke.
export default function ConnectionCard({ connection, catalog, onRevoke, busy }) {
  const status = connection.status.toLowerCase();
  const canRevoke = connection.status === "GRANTED";

  return (
    <div className={`card connection ${status}`}>
      <div className="card-head">
        <h3>{connection.sourceLabel}</h3>
        <span className={`badge status-${status}`}>{connection.status}</span>
      </div>

      <p className="expiry">{expiryLabel(connection)}</p>

      <div className="scopes">
        {connection.scopes.map((scope) => (
          <ScopeChip key={scope} scope={scope} catalog={catalog} />
        ))}
      </div>

      <p className="accounts">
        {connection.accountIds.length} account
        {connection.accountIds.length === 1 ? "" : "s"}
      </p>

      <button
        className="btn-revoke"
        disabled={!canRevoke || busy}
        onClick={() => onRevoke(connection.connectionId)}
      >
        {canRevoke ? "Revoke access" : "Access ended"}
      </button>
    </div>
  );
}
