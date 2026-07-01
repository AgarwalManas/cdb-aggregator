import { useCallback, useEffect, useState } from "react";

import {
  getAccounts,
  getAuditChain,
  getConnections,
  getReceipts,
  getSources,
  getTransactions,
  grantConnection,
  revokeConnection,
} from "../api.js";
import ActivityLog from "../components/ActivityLog.jsx";
import ChainVerifier from "../components/ChainVerifier.jsx";
import ConnectForm from "../components/ConnectForm.jsx";
import ConnectionCard from "../components/ConnectionCard.jsx";
import PermissionSimulator from "../components/PermissionSimulator.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useToast } from "../components/Toaster.jsx";

// Control Centre (slice 3): the consent + traceability hub, split into two
// sub-tabs — Connectors (connections, the expandable permission preview, connect
// a source, and the permission simulator) and Activity Logs (the verifiable
// hash chain, the audit table, and the legible access receipts).
const SUBTABS = [
  ["connectors", "Connectors"],
  ["logs", "Activity Logs"],
];

export default function ConsentPage({ scopeCatalog }) {
  const toast = useToast();
  const [sub, setSub] = useState("connectors");
  const [connections, setConnections] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [chain, setChain] = useState(null);
  const [receipts, setReceipts] = useState(null);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [conns, accts, txns, chainData, receiptData] = await Promise.all([
      getConnections(),
      getAccounts(),
      getTransactions(),
      getAuditChain(),
      getReceipts(),
    ]);
    setConnections(conns);
    setAccounts(accts);
    setTransactions(txns);
    setChain(chainData);
    setReceipts(receiptData);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        setSources(await getSources());
        await refresh();
      } catch (err) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [refresh]);

  async function withBusy(fn, successMsg) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await refresh();
      if (successMsg) toast(successMsg);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  const onRevoke = (id) => withBusy(() => revokeConnection(id), "Access revoked.");
  const onGrant = (body) => {
    const label = sources.find((s) => s.sourceId === body.sourceId)?.sourceLabel ?? "source";
    return withBusy(() => grantConnection(body), `Connected ${label}.`);
  };

  return (
    <>
      {error && <div className="error">{error}</div>}

      <nav className="subtabs" aria-label="Control Centre views">
        {SUBTABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={sub === key ? "active" : ""}
            aria-current={sub === key ? "page" : undefined}
            onClick={() => setSub(key)}
          >
            {label}
          </button>
        ))}
      </nav>

      {sub === "connectors" && (
        <>
          <section>
            <h2>Your connected sources</h2>
            <p className="section-note">
              Manage permissions per source. Expand one to see exactly what it can access —
              illustrated with your real, consent-gated sample data.
            </p>
            {loading ? (
              <SkeletonCard lines={4} />
            ) : (
              <div className="connection-list">
                {connections.map((c) => (
                  <ConnectionCard
                    key={c.connectionId}
                    connection={c}
                    catalog={scopeCatalog}
                    accounts={accounts}
                    transactions={transactions}
                    onRevoke={onRevoke}
                    busy={busy}
                  />
                ))}
              </div>
            )}
          </section>

          {!loading && sources.length > 0 && (
            <section>
              <h2>Connect a source</h2>
              <ConnectForm
                sources={sources}
                scopeCatalog={scopeCatalog}
                onGrant={onGrant}
                busy={busy}
              />
            </section>
          )}

          {!loading && Object.keys(scopeCatalog).length > 0 && (
            <section>
              <h2>Preview a permission</h2>
              <PermissionSimulator scopeCatalog={scopeCatalog} />
            </section>
          )}
        </>
      )}

      {sub === "logs" && (
        <>
          <section>
            <h2>Verify integrity</h2>
            {loading ? <SkeletonCard lines={3} /> : <ChainVerifier chain={chain} />}
          </section>

          <section>
            <h2>Activity log</h2>
            <p className="section-note">
              Every access is recorded — allowed or denied — tied to the grant that permitted it.
              Expand any row for the full receipt; tick rows and export the selection.
            </p>
            {loading ? (
              <SkeletonCard lines={6} />
            ) : (
              <ActivityLog receipts={receipts} catalog={scopeCatalog} />
            )}
          </section>
        </>
      )}
    </>
  );
}
