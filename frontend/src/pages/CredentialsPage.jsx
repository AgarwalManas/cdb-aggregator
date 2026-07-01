import { useEffect, useState } from "react";

import { getAttestationCatalog, issueAttestation, verifyAttestation } from "../api.js";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useToast } from "../components/Toaster.jsx";
import { formatDateTime } from "../format.js";

// Selective-disclosure attestations (item-32, simulated): prove a derived fact —
// "holds at least $10,000 in liquid assets" — and share only that signed
// conclusion, never the balances behind it. Clearly labelled as a simulation:
// computed and signed server-side with a demo key, not a real ZK proof.
export default function CredentialsPage() {
  const toast = useToast();
  const [catalog, setCatalog] = useState(null);
  const [issued, setIssued] = useState({}); // factId → attestation
  const [results, setResults] = useState({}); // factId → { valid, reason, tampered }
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getAttestationCatalog()
      .then(setCatalog)
      .catch((err) => setError(String(err)));
  }, []);

  async function withBusy(fn) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  const prove = (factId) =>
    withBusy(async () => {
      const att = await issueAttestation(factId);
      setIssued((prev) => ({ ...prev, [factId]: att }));
      setResults((prev) => ({ ...prev, [factId]: null }));
      toast("Attestation issued — only the conclusion, signed.");
    });

  const check = (factId, tamper) =>
    withBusy(async () => {
      const att = issued[factId];
      const presented = tamper ? { ...att, holds: !att.holds } : att;
      const res = await verifyAttestation(presented);
      setResults((prev) => ({ ...prev, [factId]: { ...res, tampered: tamper } }));
    });

  if (!catalog) {
    return error ? <div className="error">{error}</div> : <SkeletonCard lines={6} />;
  }

  return (
    <>
      {error && <div className="error">{error}</div>}

      <div className="sim-banner">
        <strong>Simulation.</strong> This demonstrates selective disclosure / zero-knowledge. Each
        fact is computed and signed server-side on mock data with a demo key — it is not a real
        zero-knowledge proof. A production version would use SD-JWT VC / range proofs and an
        asymmetric issuer key.
      </div>

      <section>
        <h2>Prove without sharing</h2>
        <p className="section-note">
          Share a conclusion, not the data behind it. Issue a signed attestation of a derived fact;
          the underlying balances and transactions never leave.
        </p>
        <div className="proof-grid">
          {catalog.map((fact) => {
            const att = issued[fact.factId];
            const result = results[fact.factId];
            return (
              <div key={fact.factId} className="card proof">
                <h3>{fact.question}</h3>
                <p className="section-note">{fact.disclosure}</p>

                {att ? (
                  <div className="attestation">
                    <div className="card-head">
                      <span className="attest-claim">{att.claim}</span>
                      <span className={`badge status-${att.holds ? "granted" : "revoked"}`}>
                        {att.holds ? "YES" : "NO"}
                      </span>
                    </div>
                    <dl className="authority-meta">
                      <div>
                        <dt>Issuer</dt>
                        <dd>{att.issuer}</dd>
                      </div>
                      <div>
                        <dt>Issued</dt>
                        <dd>{formatDateTime(att.issuedAt)}</dd>
                      </div>
                      <div>
                        <dt>Algorithm</dt>
                        <dd>{att.algorithm}</dd>
                      </div>
                      <div>
                        <dt>Signature</dt>
                        <dd>
                          <code>{att.signature.slice(0, 12)}…</code>
                        </dd>
                      </div>
                    </dl>
                    <div className="proof-actions">
                      <button className="btn-primary" disabled={busy} onClick={() => check(fact.factId, false)}>
                        Verify signature
                      </button>
                      <button className="btn-revoke" disabled={busy} onClick={() => check(fact.factId, true)}>
                        Tamper &amp; re-verify
                      </button>
                    </div>
                    {result && (
                      <div className={`verify-result ${result.valid ? "ok" : "broken"}`}>
                        {result.tampered && result.valid === false
                          ? `Caught it — ${result.reason}`
                          : result.reason}
                      </div>
                    )}
                  </div>
                ) : (
                  <button className="btn-primary" disabled={busy} onClick={() => prove(fact.factId)}>
                    Prove this
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}
