import { formatDate } from "../format.js";
import ConfirmButton from "./ConfirmButton.jsx";
import ScopeChip from "./ScopeChip.jsx";

// The agent's identity + the delegation governing it: scoped, time-limited,
// revocable — the same consent machinery, pointed at an AI agent.
export default function DelegationCard({ delegation, catalog, onDelegate, onRevoke, busy }) {
  if (!delegation) return null;
  const active = delegation.status === "GRANTED";
  const status = delegation.status.toLowerCase();

  return (
    <div className="card delegation">
      <div className="card-head">
        <h3>🤖 {delegation.agentName}</h3>
        <span className={`badge status-${active ? "granted" : status === "none" ? "expired" : status}`}>
          {delegation.status === "NONE" ? "NOT DELEGATED" : delegation.status}
        </span>
      </div>
      <p className="agent-desc">{delegation.description}</p>

      {active && (
        <>
          <div className="scopes">
            {delegation.scopes.map((s) => (
              <ScopeChip key={s} scope={s} catalog={catalog} />
            ))}
          </div>
          <p className="expiry">
            {delegation.accountIds.length} account{delegation.accountIds.length === 1 ? "" : "s"} ·
            expires {formatDate(delegation.expiresAt)}
          </p>
        </>
      )}

      {active ? (
        <ConfirmButton
          label="Revoke delegation"
          confirmLabel="Confirm — revoke delegation"
          onConfirm={onRevoke}
          busy={busy}
        />
      ) : (
        <button className="btn-primary" disabled={busy} onClick={onDelegate}>
          Delegate this task
        </button>
      )}
    </div>
  );
}
