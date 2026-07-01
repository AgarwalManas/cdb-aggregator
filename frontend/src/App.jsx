import { useCallback, useEffect, useState } from "react";

import {
  getAudit,
  getConnections,
  getScopes,
  getSources,
  grantConnection,
  revokeConnection,
} from "./api.js";
import AuditTable from "./components/AuditTable.jsx";
import ConnectForm from "./components/ConnectForm.jsx";
import ConnectionCard from "./components/ConnectionCard.jsx";

export default function App() {
  const [scopeCatalog, setScopeCatalog] = useState({});
  const [sources, setSources] = useState([]);
  const [connections, setConnections] = useState([]);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [conns, events] = await Promise.all([getConnections(), getAudit()]);
    setConnections(conns);
    setAudit(events);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [scopeList, sourceList] = await Promise.all([getScopes(), getSources()]);
        setScopeCatalog(Object.fromEntries(scopeList.map((s) => [s.scope, s])));
        setSources(sourceList);
        await refresh();
      } catch (err) {
        setError(String(err));
      }
    })();
  }, [refresh]);

  async function withBusy(fn) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  const onRevoke = (id) => withBusy(() => revokeConnection(id));
  const onGrant = (body) => withBusy(() => grantConnection(body));

  const active = connections.filter((c) => c.status === "GRANTED").length;

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>Consent &amp; Traceability</h1>
          <p className="subtitle">Choose exactly who can see your financial data — and revoke it anytime.</p>
        </div>
        <div className="who">
          <span className="avatar">AL</span>
          <div>
            <strong>Ada Lovelace</strong>
            <span className="muted">{active} active connection{active === 1 ? "" : "s"}</span>
          </div>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <section>
        <h2>Connections</h2>
        <div className="connections-grid">
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
        </div>
      </section>

      <section>
        <h2>Traceability log</h2>
        <p className="section-note">
          Every access to your data is recorded — allowed or denied — and tied to the consent that
          permitted it.
        </p>
        <AuditTable events={audit} catalog={scopeCatalog} />
      </section>

      <footer className="foot">
        cdb-aggregator · FDX-aligned consent &amp; traceability demo
      </footer>
    </div>
  );
}
