import { formatDateTime } from "../format.js";
import ScopeChip from "./ScopeChip.jsx";

// The agent's live action feed (item-28): each row is one logged read, tied to
// the grant that authorized it. When authority is paused or revoked the feed
// goes Halted and shows why — the visible proof that revoking stops the agent.
export default function ActivityFeed({ activity, catalog }) {
  if (!activity) return null;
  const { live, haltedReason, rows } = activity;

  return (
    <section className="feed-section">
      <div className="feed-head">
        <h2>Activity</h2>
        <span className={`live-dot ${live ? "on" : "off"}`}>{live ? "Live" : "Halted"}</span>
      </div>
      {!live && haltedReason && <div className="halt-banner">{haltedReason}</div>}
      {rows.length === 0 ? (
        <div className="card">
          <p className="empty">No activity yet. Run the agent to watch it read under its grant.</p>
        </div>
      ) : (
        <table className="audit activity-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Intent</th>
              <th>Account</th>
              <th>Scope</th>
              <th>Grant</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={`${r.occurredAt}-${r.action}-${r.accountId}-${i}`}
                className={r.status === "denied" ? "denied" : ""}
              >
                <td className="muted">{formatDateTime(r.occurredAt)}</td>
                <td>
                  <strong>{r.intent}</strong>
                </td>
                <td>
                  {r.accountId || "—"}
                  {r.sourceLabel && <span className="muted"> · {r.sourceLabel}</span>}
                </td>
                <td>
                  <ScopeChip scope={r.scope} catalog={catalog} />
                </td>
                <td>
                  <code>{r.authorizingConsentId || "—"}</code>
                </td>
                <td className={r.status === "authorized" ? "by-agent" : "muted"}>{r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
