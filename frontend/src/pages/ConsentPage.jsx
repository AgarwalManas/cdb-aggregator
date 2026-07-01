import { useCallback, useEffect, useState } from "react";

import { getAudit, getConnections, getSources, grantConnection, revokeConnection } from "../api.js";
import AuditTable from "../components/AuditTable.jsx";
import ConnectForm from "../components/ConnectForm.jsx";
import ConnectionCard from "../components/ConnectionCard.jsx";

// The consent + traceability dashboard (Item 9): connections, one-tap revoke,
// granular connect, and the audit log.
export default function ConsentPage({ scopeCatalog }) {
  const [connections, setConnections] = useState([]);
  const [audit, setAudit] = useState([]);
  const [sources, setSources] = useState([]);
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
        setSources(await getSources());
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

  return (
    <>
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
    </>
  );
}
