import { useCallback, useEffect, useState } from "react";

import {
  getAudit,
  getAuditChain,
  getAuditVerify,
  getConnections,
  getReceipts,
  getSources,
  grantConnection,
  revokeConnection,
} from "../api.js";
import AuditTable from "../components/AuditTable.jsx";
import ChainVerifier from "../components/ChainVerifier.jsx";
import ConnectForm from "../components/ConnectForm.jsx";
import ConnectionCard from "../components/ConnectionCard.jsx";
import PermissionSimulator from "../components/PermissionSimulator.jsx";
import ReceiptList from "../components/ReceiptList.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useToast } from "../components/Toaster.jsx";

// The consent + traceability dashboard (Item 9): connections, one-tap revoke,
// granular connect, and the audit log.
export default function ConsentPage({ scopeCatalog }) {
  const toast = useToast();
  const [connections, setConnections] = useState([]);
  const [audit, setAudit] = useState([]);
  const [verification, setVerification] = useState(null);
  const [chain, setChain] = useState(null);
  const [receipts, setReceipts] = useState(null);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [conns, events, verify, chainData, receiptData] = await Promise.all([
      getConnections(),
      getAudit(),
      getAuditVerify(),
      getAuditChain(),
      getReceipts(),
    ]);
    setConnections(conns);
    setAudit(events);
    setVerification(verify);
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

      <section>
        <h2>Connections</h2>
        <div className="connections-grid">
          {loading ? (
            <>
              <SkeletonCard lines={4} />
              <SkeletonCard lines={4} />
              <SkeletonCard lines={4} />
            </>
          ) : (
            <>
              {connections.map((c) => (
                <ConnectionCard
                  key={c.connectionId}
                  connection={c}
                  catalog={scopeCatalog}
                  onRevoke={onRevoke}
                  busy={busy}
                />
              ))}
              {sources.length > 0 && (
                <ConnectForm
                  sources={sources}
                  scopeCatalog={scopeCatalog}
                  onGrant={onGrant}
                  busy={busy}
                />
              )}
            </>
          )}
        </div>
      </section>

      {!loading && Object.keys(scopeCatalog).length > 0 && (
        <section>
          <h2>Preview a permission</h2>
          <PermissionSimulator scopeCatalog={scopeCatalog} />
        </section>
      )}

      <section>
        <h2>Traceability log</h2>
        <p className="section-note">
          Every access to your data is recorded — allowed or denied — and tied to the consent that
          permitted it.
        </p>
        {loading ? (
          <SkeletonCard lines={6} />
        ) : (
          <>
            <ChainVerifier chain={chain} />
            <AuditTable events={audit} catalog={scopeCatalog} verification={verification} />
          </>
        )}
      </section>

      <section>
        <h2>Access receipts</h2>
        <p className="section-note">
          The same record, made legible: each access as a receipt — who, what, under which grant,
          disclosed vs withheld — with a downloadable JSON copy.
        </p>
        {loading ? <SkeletonCard lines={6} /> : <ReceiptList receipts={receipts} />}
      </section>
    </>
  );
}
