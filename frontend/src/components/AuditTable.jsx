import { formatDateTime } from "../format.js";

// The traceability log: every access attempt, allowed or denied, with what was
// disclosed and what was minimized away.
export default function AuditTable({ events, catalog }) {
  if (!events.length) {
    return <p className="empty">No access recorded yet.</p>;
  }
  return (
    <table className="audit">
      <thead>
        <tr>
          <th>When</th>
          <th>By</th>
          <th>Action</th>
          <th>Scope</th>
          <th>Account</th>
          <th>Decision</th>
          <th>Disclosed</th>
        </tr>
      </thead>
      <tbody>
        {events.map((e, i) => (
          <tr key={i} className={e.allowed ? "allowed" : "denied"}>
            <td className="muted">{formatDateTime(e.occurredAt)}</td>
            <td>
              {e.recipient?.startsWith("agent:") ? (
                <span className="by-agent">🤖 Assistant</span>
              ) : (
                <span className="muted">Aggregator</span>
              )}
            </td>
            <td>
              <code>{e.action}</code>
            </td>
            <td>{catalog?.[e.scope]?.label || e.scope}</td>
            <td className="muted">{e.accountId || "—"}</td>
            <td>
              {e.allowed ? (
                <span className="badge status-granted">Allowed</span>
              ) : (
                <span className="badge status-revoked" title={e.reason}>
                  Denied · {e.reason}
                </span>
              )}
            </td>
            <td className="muted">
              {e.allowed ? `${e.recordCount} record${e.recordCount === 1 ? "" : "s"}` : "—"}
              {e.withheld.length > 0 && (
                <span className="withheld"> · withheld {e.withheld.join(", ")}</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
