import { useCallback, useEffect, useState } from "react";

import { exchangeToken, getAlias, repointAlias, resolveAlias } from "../api.js";
import HowItWorksStrip from "../components/HowItWorksStrip.jsx";
import Icon from "../components/Icon.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import { useToast } from "../components/Toaster.jsx";
import { formatDateTime } from "../format.js";

// Portable account alias + consent-gated resolver (item-31): the user owns a
// bank-neutral handle; resolving it returns a one-time routing token, never the
// raw bank/branch/account. Re-pointing is a scoped, logged portability event.
const HOW = [
  [
    "users",
    "Share your address",
    "Hand a counterparty your handle instead of your bank details.",
  ],
  [
    "shield",
    "They resolve it",
    "Resolution succeeds only while a consent covers the linked account.",
  ],
  [
    "key",
    "One-time token issued",
    "All they ever receive is a single-use routing token — no bank, branch, or account number.",
  ],
  [
    "check",
    "Redeemed once",
    "Settlement redeems the token; spent tokens can't be replayed. Mock only — no money moves.",
  ],
];

export default function AddressPage() {
  const toast = useToast();
  const [alias, setAlias] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [changing, setChanging] = useState(false); // "Change linked account" panel
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

  async function copyText(text, label) {
    try {
      await navigator.clipboard.writeText(text);
      toast(`${label} copied.`);
    } catch {
      toast("Copy failed — select it manually.");
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
      setChanging(false);
      toast("Address re-pointed — logged as a consent event.");
    });

  if (loading) return <SkeletonCard lines={6} />;
  if (!alias) return error ? <div className="error">{error}</div> : null;

  const currentOption = alias.options.find((o) => o.accountId === alias.target.accountId);
  const bankInitial = (currentOption?.sourceLabel || alias.target.display || "?").charAt(0);

  return (
    <>
      {error && <div className="error">{error}</div>}

      <HowItWorksStrip steps={HOW} />

      <div className="card addr-summary">
        <div className="addr-cell">
          <span className="addr-label">Your address</span>
          <div className="addr-handle-row">
            <span className="addr-handle">{alias.handle}</span>
            <button
              type="button"
              className="icon-btn"
              title="Copy address"
              onClick={() => copyText(alias.handle, "Address")}
            >
              <Icon name="copy" />
            </button>
          </div>
          <span className="badge status-granted">Active</span>
        </div>

        <div className="addr-cell">
          <span className="addr-label">Linked account</span>
          <div className="addr-linked">
            <span className="bank-tile" aria-hidden="true">
              {bankInitial}
            </span>
            <div>
              <strong>{alias.target.display}</strong>
              <span className="muted">Where the address routes</span>
            </div>
          </div>
        </div>

        <div className="addr-cell">
          <span className="addr-label">Linked since</span>
          <strong className="addr-since">
            {formatDateTime(alias.repointedAt || alias.createdAt)}
          </strong>
        </div>

        <div className="addr-cell addr-actions">
          <button
            type="button"
            className="btn-primary"
            disabled={busy}
            onClick={() => setChanging((v) => !v)}
          >
            {changing ? "Keep current account" : "Change linked account"}
          </button>
        </div>
      </div>

      {changing && (
        <div className="card repoint-panel">
          <span className="addr-label">Point {alias.handle} at</span>
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
          <p className="section-note">
            Re-pointing is a scoped, logged portability event — counterparties keep using the same
            address.
          </p>
        </div>
      )}

      <div className="card addr-facts">
        <div className="fact">
          <span className="fact-icon">
            <Icon name="users" />
          </span>
          <div>
            <span className="addr-label">Who can resolve it</span>
            <strong>Counterparties with an active consent</strong>
          </div>
        </div>
        <div className="fact">
          <span className="fact-icon">
            <Icon name="key" />
          </span>
          <div>
            <span className="addr-label">What they receive</span>
            <strong>A one-time routing token</strong>
          </div>
        </div>
        <div className="fact">
          <span className="fact-icon">
            <Icon name="fileCheck" />
          </span>
          <div>
            <span className="addr-label">Changing banks</span>
            <strong>Logged as a consent event</strong>
          </div>
        </div>
      </div>

      <section className="resolve-section">
        <h2>Resolve as a counterparty</h2>
        <p className="section-note">
          Stand in a payer&apos;s shoes: resolve <code>{alias.handle}</code> and see exactly what
          you&apos;d be told.
        </p>
        <div className="card resolve-card">
          <div className="resolve-flow">
            <code className="resolve-handle">{alias.handle}</code>
            <button className="btn-primary" disabled={busy} onClick={onResolve}>
              Resolve address
            </button>
            <span className="hiw-arrow" aria-hidden="true">
              <Icon name="arrowRight" />
            </span>
            {resolution?.allowed ? (
              <span className="token-box">
                <code>{resolution.routingToken}</code>
                <button
                  type="button"
                  className="icon-btn"
                  title="Copy token"
                  onClick={() => copyText(resolution.routingToken, "Token")}
                >
                  <Icon name="copy" />
                </button>
              </span>
            ) : (
              <span className="token-box token-empty">
                {resolution
                  ? `Refused — ${resolution.reason || "no active consent"}. Nothing was issued.`
                  : "The one-time routing token appears here."}
              </span>
            )}
          </div>

          {resolution?.allowed && (
            <div className="resolve-after">
              <span className="resolve-note">
                <Icon name="shieldCheck" />
                This is all a counterparty ever sees — no bank, branch, or account number.
              </span>
              <button
                className="btn-revoke"
                disabled={busy || tokenState === "spent"}
                onClick={onRedeem}
              >
                {tokenState === "spent" ? "Token spent" : "Redeem token (as settlement)"}
              </button>
            </div>
          )}

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
          {tokenState === "spent" && coords && (
            <p className="muted">Revealed once, to settle — the token is now spent.</p>
          )}
          {tokenState === "gone" && (
            <p className="muted">That token was already used — single-use, by design.</p>
          )}
        </div>
      </section>

      <section>
        <h2>Recent address activity</h2>
        {alias.history.length === 0 ? (
          <div className="card">
            <p className="empty">No resolutions yet — try resolving your address above.</p>
          </div>
        ) : (
          <div className="audit-scroll">
            <table className="audit">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Who</th>
                  <th>What they received</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {alias.history.map((h, i) => (
                  <tr key={`${h.occurredAt}-${i}`} className={h.allowed ? "" : "denied"}>
                    <td className="muted">{formatDateTime(h.occurredAt)}</td>
                    <td>{h.requester}</td>
                    <td>{h.disclosed}</td>
                    <td>
                      {h.allowed ? (
                        <span className="result-ok">
                          <Icon name="check" />
                          Resolved
                        </span>
                      ) : (
                        <span className="muted">{h.reason || "denied"}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
