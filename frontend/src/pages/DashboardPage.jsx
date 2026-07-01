import { useEffect, useState } from "react";

import { getAlias, getAuditVerify, getConnections, getNetWorth, getReceipts } from "../api.js";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { formatDateTime, formatMoney } from "../format.js";

// Dashboard (slice 2): a real data-sharing overview, computed entirely from the
// existing endpoints — active connections, what's been accessed, the portable
// address, recent activity, and a monochrome "data you've shared" breakdown.
// No invented data and no faux trend deltas; just the honest counts.
export default function DashboardPage({ onNavigate }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [hint, setHint] = useState(true);

  useEffect(() => {
    Promise.all([getConnections(), getReceipts(), getAuditVerify(), getAlias(), getNetWorth()])
      .then(([connections, receipts, verify, alias, netWorth]) =>
        setData({ connections, receipts, verify, alias, netWorth }),
      )
      .catch((err) => setError(String(err)));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <SkeletonCard lines={8} />;

  const { connections, receipts, verify, alias, netWorth } = data;
  const active = connections.filter((c) => c.status === "GRANTED");
  const categories = new Set(active.flatMap((c) => c.scopes));
  const allowed = receipts.filter((r) => r.allowed);
  const denied = receipts.filter((r) => !r.allowed);
  const recent = receipts.slice(0, 5);

  const byCluster = {};
  allowed.forEach((r) => {
    byCluster[r.clusterLabel] = (byCluster[r.clusterLabel] || 0) + 1;
  });
  const shared = Object.entries(byCluster)
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count);
  const maxShare = Math.max(1, ...shared.map((s) => s.count));

  const stats = [
    { label: "Active connections", value: active.length, note: `${active.length} of ${connections.length} sources` },
    { label: "Data categories shared", value: categories.size, note: "across your active grants" },
    { label: "Access events", value: receipts.length, note: "allowed and denied" },
    { label: "Denied / blocked", value: denied.length, note: "stopped by the consent gate" },
  ];

  return (
    <>
      {hint && (
        <div className="dash-hint">
          <span>
            New here? Revoke a bank in <strong>Control Centre</strong> and watch it disappear from{" "}
            <strong>Bank Accounts</strong> — consent, not connectivity, decides what you see.
          </span>
          <button type="button" className="hint-dismiss" onClick={() => setHint(false)} aria-label="Dismiss">
            ✕
          </button>
        </div>
      )}

      <div className="stat-row">
        {stats.map((s) => (
          <div key={s.label} className="card stat-tile">
            <span className="stat-label">{s.label}</span>
            <span className="stat-value">{s.value}</span>
            <span className="stat-note">{s.note}</span>
          </div>
        ))}
      </div>

      <div className="dash-grid">
        <section className="card dash-card">
          <div className="card-head">
            <h3>Your portable address</h3>
            <span className="badge status-granted">Active</span>
          </div>
          <p className="handle-sm">{alias.handle}</p>
          <p className="section-note">Routes to {alias.target.display}</p>
          <button type="button" className="btn-revoke" onClick={() => onNavigate("address")}>
            Manage address
          </button>
        </section>

        <section className="card dash-card">
          <div className="card-head">
            <h3>Recent activity</h3>
            <button type="button" className="link" onClick={() => onNavigate("control")}>
              View all
            </button>
          </div>
          <ul className="mini-feed">
            {recent.map((r) => (
              <li key={r.receiptId}>
                <span className="mini-main">
                  <strong>{r.accessorLabel}</strong>
                  <span className="muted">
                    {r.clusterLabel} · {formatDateTime(r.occurredAt)}
                  </span>
                </span>
                <span className={`badge status-${r.allowed ? "granted" : "revoked"}`}>
                  {r.allowed ? "Allowed" : "Denied"}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card dash-card">
          <div className="card-head">
            <h3>Data you&apos;ve shared</h3>
            <span className="muted">{allowed.length} accesses</span>
          </div>
          <ul className="share-bars">
            {shared.map((s) => (
              <li key={s.label}>
                <span className="share-label">{s.label}</span>
                <span className="share-track">
                  <span className="share-fill" style={{ width: `${(s.count / maxShare) * 100}%` }} />
                </span>
                <span className="share-count">{s.count}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="dash-grid-2">
        <section className="card dash-card">
          <div className="card-head">
            <h3>Your connected sources</h3>
            <button type="button" className="link" onClick={() => onNavigate("control")}>
              Manage
            </button>
          </div>
          <ul className="source-list">
            {connections.map((c) => {
              const isActive = c.status === "GRANTED";
              return (
                <li key={c.connectionId}>
                  <span>
                    <strong>{c.sourceLabel}</strong>
                    <span className="muted">
                      {" "}
                      · {c.accountIds.length} account{c.accountIds.length === 1 ? "" : "s"} ·{" "}
                      {c.scopes.length} scope{c.scopes.length === 1 ? "" : "s"}
                    </span>
                  </span>
                  <span className={`badge status-${isActive ? "granted" : "revoked"}`}>
                    {isActive ? "Active" : c.status}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>

        <div className="dash-side">
          <section className="card side-tile">
            <span className="stat-label">Household net worth</span>
            <span className="side-value">{formatMoney(netWorth.netWorth, netWorth.currency)}</span>
            <button type="button" className="link" onClick={() => onNavigate("accounts")}>
              See accounts →
            </button>
          </section>
          <section className="card side-tile">
            <span className="stat-label">Log integrity</span>
            <span className={`side-value ${verify.valid ? "ok" : "broken"}`}>
              {verify.valid ? "Verified intact" : "Tampered"}
            </span>
            <button type="button" className="link" onClick={() => onNavigate("control")}>
              Verify it yourself →
            </button>
          </section>
        </div>
      </div>
    </>
  );
}
