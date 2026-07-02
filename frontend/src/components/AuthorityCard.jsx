import { expiryLabel } from "../format.js";
import ConfirmButton from "./ConfirmButton.jsx";
import Icon from "./Icon.jsx";
import ScopeChip from "./ScopeChip.jsx";

// The authority card (item-28): the scoped authority the agent holds right now —
// identity, scope, time remaining — with the live controls that govern it:
// Run, Pause / Resume, and Revoke. Pausing or revoking halts the feed at once.
export default function AuthorityCard({
  authority,
  catalog,
  busy,
  onDelegate,
  onPause,
  onResume,
  onRevoke,
  onRun,
}) {
  if (!authority) return null;
  const active = authority.status === "GRANTED";
  const status = authority.status.toLowerCase();
  const badgeClass = active ? "granted" : status === "none" ? "expired" : status;
  const badgeText =
    authority.status === "NONE" ? "NOT DELEGATED" : authority.paused ? "PAUSED" : authority.status;

  return (
    <div className="card authority">
      <div className="card-head">
        <h3 className="agent-name">
          <span className="agent-ico">
            <Icon name="sparkle" />
          </span>
          {authority.agentName}
        </h3>
        <span className={`badge status-${authority.paused && active ? "pending" : badgeClass}`}>
          {badgeText}
        </span>
      </div>
      <p className="agent-desc">{authority.description}</p>

      {active ? (
        <>
          <div className="scopes">
            {authority.scopes.map((s) => (
              <ScopeChip key={s} scope={s} catalog={catalog} />
            ))}
          </div>
          <dl className="authority-meta">
            <div>
              <dt>Accounts</dt>
              <dd>{authority.accountIds.length}</dd>
            </div>
            <div>
              <dt>Authority</dt>
              <dd>{expiryLabel(authority)}</dd>
            </div>
            <div>
              <dt>State</dt>
              <dd>{authority.paused ? "Paused — not acting" : "Live — can act"}</dd>
            </div>
          </dl>
          <div className="authority-controls">
            <button className="btn-primary" disabled={busy || authority.paused} onClick={onRun}>
              Run now
            </button>
            {authority.paused ? (
              <button className="btn-revoke" disabled={busy} onClick={onResume}>
                Resume
              </button>
            ) : (
              <button className="btn-revoke" disabled={busy} onClick={onPause}>
                Pause
              </button>
            )}
          </div>
          <ConfirmButton
            label="Revoke authority"
            confirmLabel="Confirm — revoke authority"
            onConfirm={onRevoke}
            busy={busy}
          />
        </>
      ) : (
        <button className="btn-primary" disabled={busy} onClick={onDelegate}>
          Delegate this task
        </button>
      )}
    </div>
  );
}
