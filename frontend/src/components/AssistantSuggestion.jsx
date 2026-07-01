import { formatMoney, formatPct } from "../format.js";

// The agent's advisory output — a suggestion, never an action.
export default function AssistantSuggestion({ suggestion }) {
  if (!suggestion) return null;
  const { idleCash, currency, estimatedAnnualGain, targetRate, thresholdRate, analyzed, notCounted } =
    suggestion;

  if (!analyzed.length) {
    return (
      <div className="card">
        <p className="empty">No idle cash found — everything is already working.</p>
      </div>
    );
  }

  return (
    <div className="card suggestion">
      <p className="suggestion-lead">
        You have <strong>{formatMoney(idleCash, currency)}</strong> earning under{" "}
        {formatPct(thresholdRate)}. Moving it to a ~{formatPct(targetRate)} option could earn about{" "}
        <strong className="pos">{formatMoney(estimatedAnnualGain, currency)}/year</strong> more.
      </p>

      <table className="audit">
        <thead>
          <tr>
            <th>Account</th>
            <th>Source</th>
            <th>Balance</th>
            <th>Rate</th>
            <th>Idle</th>
            <th>Est. gain / yr</th>
          </tr>
        </thead>
        <tbody>
          {analyzed.map((a) => (
            <tr key={a.accountId}>
              <td>
                <strong>{a.label}</strong>
              </td>
              <td className="muted">{a.sourceLabel || "—"}</td>
              <td>{formatMoney(a.balance, currency)}</td>
              <td className="muted">{formatPct(a.rate)}</td>
              <td>{formatMoney(a.idle, currency)}</td>
              <td className="pos">{formatMoney(a.estimatedGain, currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {notCounted.length > 0 && (
        <p className="section-note">
          Not counted: {notCounted.map((n) => `${n.accountId} (${n.reason})`).join(", ")}.
        </p>
      )}

      <p className="advisory">{suggestion.advisory}</p>
    </div>
  );
}
