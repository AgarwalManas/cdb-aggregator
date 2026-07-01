import { useEffect, useMemo, useState } from "react";

import {
  getAttestationCatalog,
  getVerifiers,
  issueAttestation,
  presentCredentials,
} from "../api.js";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useToast } from "../components/Toaster.jsx";

// Selective-disclosure attestations (item-32) + a holder wallet that presents a
// chosen subset to a verifier (item-33). Simulated end to end: facts are
// computed and signed server-side with a demo key, and the "wallet" is
// browser-held — a demonstration of the OID4VP-style holder → verifier flow, not
// a real credential wallet.
export default function CredentialsPage() {
  const toast = useToast();
  const [catalog, setCatalog] = useState(null);
  const [verifiers, setVerifiers] = useState(null);
  const [wallet, setWallet] = useState({}); // factId → attestation (held credentials)
  const [selected, setSelected] = useState(() => new Set());
  const [verifierId, setVerifierId] = useState(null);
  const [tamper, setTamper] = useState(false);
  const [presentation, setPresentation] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([getAttestationCatalog(), getVerifiers()])
      .then(([facts, vs]) => {
        setCatalog(facts);
        setVerifiers(vs);
        setVerifierId(vs[0]?.verifierId ?? null);
      })
      .catch((err) => setError(String(err)));
  }, []);

  const verifier = useMemo(
    () => verifiers?.find((v) => v.verifierId === verifierId) ?? null,
    [verifiers, verifierId],
  );

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

  const addToWallet = (factId) =>
    withBusy(async () => {
      const att = await issueAttestation(factId);
      setWallet((prev) => ({ ...prev, [factId]: att }));
      setPresentation(null);
      toast("Credential added to your wallet.");
    });

  function toggleSelect(factId) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(factId)) next.delete(factId);
      else next.add(factId);
      return next;
    });
    setPresentation(null);
  }

  const present = () =>
    withBusy(async () => {
      const chosen = [...selected].map((factId) => {
        const att = wallet[factId];
        return tamper ? { ...att, holds: !att.holds } : att; // demo: break a signature
      });
      setPresentation(await presentCredentials(verifierId, chosen));
      toast("Presented to the verifier.");
    });

  if (!catalog || !verifiers) {
    return error ? <div className="error">{error}</div> : <SkeletonCard lines={6} />;
  }

  const held = Object.values(wallet);

  return (
    <>
      {error && <div className="error">{error}</div>}

      <div className="sim-banner">
        <strong>Simulation.</strong> Selective disclosure end to end: facts are computed and signed
        server-side on mock data with a demo key, and the wallet is held in your browser. It
        demonstrates the holder → verifier presentation flow (OID4VP-style) — not a real ZK proof
        or credential wallet. Production would use W3C VC / SD-JWT and asymmetric issuer keys.
      </div>

      <section>
        <h2>Prove without sharing</h2>
        <p className="section-note">
          Issue a signed attestation of a derived fact into your wallet. The underlying balances and
          transactions never leave — only the conclusion is signed.
        </p>
        <div className="proof-grid">
          {catalog.map((fact) => {
            const inWallet = Boolean(wallet[fact.factId]);
            return (
              <div key={fact.factId} className="card proof">
                <h3>{fact.question}</h3>
                <p className="section-note">{fact.disclosure}</p>
                <button
                  className={inWallet ? "btn-revoke" : "btn-primary"}
                  disabled={busy || inWallet}
                  onClick={() => addToWallet(fact.factId)}
                >
                  {inWallet ? "In your wallet ✓" : "Add to wallet"}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <section>
        <h2>Your wallet</h2>
        {held.length === 0 ? (
          <div className="card">
            <p className="empty">Your wallet is empty. Add a credential above.</p>
          </div>
        ) : (
          <>
            <p className="section-note">
              Held credentials. Tick the ones to disclose — you present only what a verifier needs.
            </p>
            <div className="wallet-grid">
              {held.map((att) => {
                const on = selected.has(att.factId);
                return (
                  <label key={att.factId} className={`card credential ${on ? "picked" : ""}`}>
                    <input type="checkbox" checked={on} onChange={() => toggleSelect(att.factId)} />
                    <span className="credential-body">
                      <span className="credential-claim">{att.claim}</span>
                      <span className="credential-meta">
                        <span className={`badge status-${att.holds ? "granted" : "revoked"}`}>
                          {att.holds ? "YES" : "NO"}
                        </span>
                        <code>{att.signature.slice(0, 10)}…</code>
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
          </>
        )}
      </section>

      <section>
        <h2>Present to a verifier</h2>
        <p className="section-note">
          Pick who&apos;s asking. They see only whether each required fact is met — never your data.
        </p>
        <div className="verifier-tabs">
          {verifiers.map((v) => (
            <button
              key={v.verifierId}
              className={v.verifierId === verifierId ? "btn-primary" : "btn-revoke"}
              onClick={() => {
                setVerifierId(v.verifierId);
                setPresentation(null);
              }}
            >
              {v.name}
            </button>
          ))}
        </div>

        {verifier && (
          <div className="card verifier-card">
            <p className="section-note">{verifier.purpose}. It needs to see:</p>
            <ul className="preview-list">
              {verifier.requirements.map((r) => (
                <li key={r.factId}>
                  <strong>{r.question}</strong> <span className="muted">→ must be “yes”</span>
                </li>
              ))}
            </ul>
            <label className="tamper-toggle">
              <input type="checkbox" checked={tamper} onChange={() => setTamper((t) => !t)} />
              Present tampered copies (demo — the verifier should reject them)
            </label>
            <button className="btn-primary" disabled={busy || selected.size === 0} onClick={present}>
              Present {selected.size} selected credential{selected.size === 1 ? "" : "s"}
            </button>

            {presentation && (
              <div className="presentation">
                <div
                  className={`verify-result ${presentation.accepted ? "ok" : "broken"}`}
                >
                  {presentation.accepted
                    ? `Accepted — every required fact was proven from ${presentation.presentedCount} credential${presentation.presentedCount === 1 ? "" : "s"}.`
                    : "Rejected — not every requirement was met."}
                </div>
                <ul className="requirement-list">
                  {presentation.results.map((r) => (
                    <li key={r.factId} className={r.satisfied ? "met" : "unmet"}>
                      <span className="req-icon" aria-hidden="true">
                        {r.satisfied ? "✓" : "✕"}
                      </span>
                      <span>
                        <strong>{r.question}</strong>
                        <span className="muted"> — {r.detail}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>
    </>
  );
}
