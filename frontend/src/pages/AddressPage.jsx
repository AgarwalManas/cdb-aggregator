import { useCallback, useEffect, useState } from "react";

import { exchangeToken, getAlias, repointAlias, resolveAlias } from "../api.js";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useToast } from "../components/Toaster.jsx";
import { formatDateTime } from "../format.js";

// Portable account alias + consent-gated resolver (item-31): the user owns a
// bank-neutral handle; resolving it returns a one-time routing token, never the
// raw bank/branch/account. Re-pointing is a scoped, logged portability event.
export default function AddressPage() {
  const toast = useToast();
  const [alias, setAlias] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [resolution, setResolution] = useState(null); // last resolve result
  const [coords, setCoords] = useState(null); // last redeemed coordinates
  const [tokenState, setTokenState] = useState(null); // "spent" once redeemed/gone

  const load = useCallback(async () => {
    setAlias(await getAlias());
  }, []);

  useEffect(() => {
    load()
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [load]);

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

  const onResolve = () =>
    withBusy(async () => {
      const res = await resolveAlias({ requester: "counterparty:acme-payments" });
      setResolution(res);
      setCoords(null);
      setTokenState(null);
      await load();
      toast(res.allowed ? "Resolved — a one-time token was issued." : "Resolution refused.");
    });

  const onRedeem = () =>
    withBusy(async () => {
      try {
        setCoords(await exchangeToken(resolution.routingToken));
        setTokenState("spent");
        toast("Token redeemed — coordinates revealed once.");
      } catch {
        // 410: the token was already used or expired.
        setCoords(null);
        setTokenState("gone");
        toast("That token is spent.");
      }
    });

  const onRepoint = (accountId) =>
    withBusy(async () => {
      setAlias(await repointAlias(accountId));
      setResolution(null);
      setCoords(null);
      toast("Alias re-pointed — logged as a consent event.");
    });

  if (loading) return <SkeletonCard lines={6} />;
  if (!alias) return error ? <div className="error">{error}</div> : null;

  return (
    <>
      {error && <div className="error">{error}</div>}

      <p className="section-note console-intro">
        A bank-neutral address you own. A counterparty resolves it to a one-time routing token —
        never your bank, branch, or account number — and only while a consent covers the target.
        Re-pointing it to another bank is a scoped, logged event. Mock addressing only: no money
        moves and nothing settles.
      </p>

      <div className="agent-cols">
        <section>
          <h2>Your address</h2>
          <div className="card address-card">
            <div className="handle">{alias.handle}</div>
            <dl className="authority-meta">
              <div>
                <dt>Routes to</dt>
                <dd>{alias.target.display}</dd>
              </div>
              <div>
                <dt>Since</dt>
                <dd>{formatDateTime(alias.repointedAt || alias.createdAt)}</dd>
              </div>
            </dl>

            <div className="repoint">
              <span className="repoint-label">Change bank</span>
              <div className="repoint-options">
                {alias.options.map((o) => {
                  const current = o.accountId === alias.target.accountId;
                  return (
                    <button
                      key={o.accountId}
                      className={`repoint-option ${current ? "btn-primary" : "btn-revoke"}`}
                      disabled={busy || current}
                      onClick={() => onRepoint(o.accountId)}
                      title={o.display}
                    >
                      <span className="repoint-bank">{o.sourceLabel}</span>
                      <span className="repoint-acct">
                        {o.display.replace(`${o.sourceLabel} `, "")}
                        {current ? " · current" : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        <div className="console-main">
          <section className="resolve-section">
            <h2>Resolve as a counterparty</h2>
            <p className="section-note">
              Stand in a payer&apos;s shoes: resolve <code>{alias.handle}</code> and see exactly
              what you&apos;d be told.
            </p>
            <button className="btn-primary" disabled={busy} onClick={onResolve}>
              Resolve address
            </button>

            {resolution && (
              <div className={`card resolution ${resolution.allowed ? "" : "denied-card"}`}>
                {resolution.allowed ? (
                  <>
                    <p className="section-note">You were handed a one-time routing token:</p>
                    <code className="token">{resolution.routingToken}</code>
                    <p className="advisory">
                      This is all a counterparty ever sees — no bank, no branch, no account number.
                    </p>
                    <button
                      className="btn-revoke"
                      disabled={busy || tokenState === "spent"}
                      onClick={onRedeem}
                    >
                      {tokenState === "spent" ? "Token spent" : "Redeem token (as settlement)"}
                    </button>
                    {coords && (
                      <dl className="authority-meta coords">
                        <div>
                          <dt>Institution</dt>
                          <dd>{coords.institution}</dd>
                        </div>
                        <div>
                          <dt>Transit</dt>
                          <dd>{coords.transit}</dd>
                        </div>
                        <div>
                          <dt>Account</dt>
                          <dd>{coords.maskedAccount}</dd>
                        </div>
                      </dl>
                    )}
                    {tokenState === "gone" && (
                      <p className="muted">That token was already used — single-use, by design.</p>
                    )}
                  </>
                ) : (
                  <>
                    <p className="section-note">Resolution refused — the counterparty got nothing.</p>
                    <p className="muted">Reason: {resolution.reason || "no active consent"}.</p>
                  </>
                )}
              </div>
            )}
          </section>

          <section className="resolve-section">
            <h2>Who resolved this</h2>
            {alias.history.length === 0 ? (
              <div className="card">
                <p className="empty">No resolutions yet.</p>
              </div>
            ) : (
              <table className="audit">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Who</th>
                    <th>Told</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {alias.history.map((h, i) => (
                    <tr key={`${h.occurredAt}-${i}`} className={h.allowed ? "" : "denied"}>
                      <td className="muted">{formatDateTime(h.occurredAt)}</td>
                      <td>{h.requester}</td>
                      <td>{h.disclosed}</td>
                      <td className={h.allowed ? "by-agent" : "muted"}>
                        {h.allowed ? "resolved" : h.reason || "denied"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      </div>
    </>
  );
}
