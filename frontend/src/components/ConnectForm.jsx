import { useState } from "react";

const DEFAULT_SCOPES = ["ACCOUNT_DETAILS", "BALANCES", "TRANSACTIONS"];

// Connect (grant consent to) a data source, choosing exactly which scopes to
// share — the "granular consent" story, made interactive.
export default function ConnectForm({ sources, scopeCatalog, onGrant, busy }) {
  const scopeKeys = Object.keys(scopeCatalog);
  const [sourceId, setSourceId] = useState(sources[0]?.sourceId ?? "");
  const [scopes, setScopes] = useState(new Set(DEFAULT_SCOPES));
  const [durationDays, setDurationDays] = useState(90);

  function toggle(scope) {
    setScopes((prev) => {
      const next = new Set(prev);
      next.has(scope) ? next.delete(scope) : next.add(scope);
      return next;
    });
  }

  function submit(e) {
    e.preventDefault();
    if (!sourceId || scopes.size === 0) return;
    onGrant({ sourceId, scopes: [...scopes], durationDays: Number(durationDays) });
  }

  return (
    <form className="card connect-form" onSubmit={submit}>
      <h3>Connect a source</h3>

      <label>
        Source
        <select value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
          {sources.map((s) => (
            <option key={s.sourceId} value={s.sourceId}>
              {s.sourceLabel}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="scope-picker">
        <legend>Share only what you choose</legend>
        {scopeKeys.map((scope) => (
          <label key={scope} className="scope-check">
            <input type="checkbox" checked={scopes.has(scope)} onChange={() => toggle(scope)} />
            {scopeCatalog[scope].label}
          </label>
        ))}
      </fieldset>

      <label>
        Expires after (days)
        <input
          type="number"
          min="1"
          max="365"
          value={durationDays}
          onChange={(e) => setDurationDays(e.target.value)}
        />
      </label>

      <button className="btn-primary" type="submit" disabled={busy || scopes.size === 0}>
        Grant access
      </button>
    </form>
  );
}
