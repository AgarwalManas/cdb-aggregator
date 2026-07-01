import { useMemo, useState } from "react";

import { formatDateTime } from "../format.js";

// aggregator vs delegated agent, derived from the recipient identity.
function actorOf(recipient) {
  return recipient?.startsWith("agent:") ? "agent" : "aggregator";
}

function SortHeader({ label, active, dir, onClick }) {
  return (
    <th aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" className="th-sort" onClick={onClick}>
        {label}
        <span className="sort-caret" aria-hidden="true">
          {active ? (dir === "asc" ? "▲" : "▼") : "⇅"}
        </span>
      </button>
    </th>
  );
}

// The traceability log (item-9), upgraded (item-17) with filter / sort / search
// and a tamper-evident chain badge (item-22). Every access attempt is here,
// allowed or denied, tied to the grant it relied on.
export default function AuditTable({ events, catalog, verification }) {
  const [actor, setActor] = useState("all");
  const [decision, setDecision] = useState("all");
  const [scope, setScope] = useState("all");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState("time");
  const [sortDir, setSortDir] = useState("desc");

  const scopes = useMemo(() => Array.from(new Set(events.map((e) => e.scope))).sort(), [events]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = events.filter((e) => {
      if (actor !== "all" && actorOf(e.recipient) !== actor) return false;
      if (decision === "allowed" && !e.allowed) return false;
      if (decision === "denied" && e.allowed) return false;
      if (scope !== "all" && e.scope !== scope) return false;
      if (q) {
        const hay = [e.action, e.accountId, e.scope, e.recipient, e.reason, catalog?.[e.scope]?.label]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    const dir = sortDir === "asc" ? 1 : -1;
    const keyOf = (e) => (sortKey === "actor" ? actorOf(e.recipient) : e.occurredAt);
    return [...filtered].sort((a, b) => {
      const ka = keyOf(a);
      const kb = keyOf(b);
      return ka < kb ? -dir : ka > kb ? dir : 0;
    });
  }, [events, actor, decision, scope, query, sortKey, sortDir, catalog]);

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "time" ? "desc" : "asc");
    }
  }

  function clearFilters() {
    setActor("all");
    setDecision("all");
    setScope("all");
    setQuery("");
  }

  return (
    <div className="log">
      <div className="log-bar">
        <div className="log-controls">
          <select aria-label="Filter by actor" value={actor} onChange={(e) => setActor(e.target.value)}>
            <option value="all">All actors</option>
            <option value="aggregator">Aggregator</option>
            <option value="agent">Assistant</option>
          </select>
          <select
            aria-label="Filter by decision"
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
          >
            <option value="all">All decisions</option>
            <option value="allowed">Allowed</option>
            <option value="denied">Denied</option>
          </select>
          <select aria-label="Filter by scope" value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="all">All scopes</option>
            {scopes.map((s) => (
              <option key={s} value={s}>
                {catalog?.[s]?.label || s}
              </option>
            ))}
          </select>
          <input
            type="search"
            className="log-search"
            placeholder="Search the log…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search the log"
          />
        </div>
        {verification && (
          <span
            className={`badge chain ${verification.valid ? "chain-ok" : "chain-broken"}`}
            title={
              verification.valid
                ? `All ${verification.checked} entries verify against the hash chain.`
                : `Chain integrity broken at entry ${verification.brokenAt}.`
            }
          >
            {verification.valid ? `Chain verified ✓ · ${verification.checked}` : "Chain broken ✕"}
          </span>
        )}
      </div>

      {events.length === 0 ? (
        <p className="empty">No access recorded yet.</p>
      ) : visible.length === 0 ? (
        <p className="empty">
          No entries match these filters.{" "}
          <button type="button" className="link" onClick={clearFilters}>
            Clear filters
          </button>{" "}
          to see all {events.length}.
        </p>
      ) : (
        <div className="audit-scroll">
          <table className="audit">
            <thead>
            <tr>
              <SortHeader
                label="When"
                active={sortKey === "time"}
                dir={sortDir}
                onClick={() => toggleSort("time")}
              />
              <SortHeader
                label="By"
                active={sortKey === "actor"}
                dir={sortDir}
                onClick={() => toggleSort("actor")}
              />
              <th>Action</th>
              <th>Scope</th>
              <th>Account</th>
              <th>Decision</th>
              <th>Disclosed</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((e, i) => (
              <tr key={i} className={e.allowed ? "allowed" : "denied"}>
                <td className="muted">{formatDateTime(e.occurredAt)}</td>
                <td>
                  {actorOf(e.recipient) === "agent" ? (
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
        </div>
      )}
    </div>
  );
}
