import { useState } from "react";

import { expiryLabel, formatDateTime, formatMoney } from "../format.js";
import ConfirmButton from "./ConfirmButton.jsx";
import ScopeChip from "./ScopeChip.jsx";

// One connected data source: status, scopes, expiry, one-tap revoke — and an
// expandable preview of exactly what it can access, illustrated with the real
// (consent-gated) sample data: a sample account and a sample transaction.
export default function ConnectionCard({
  connection,
  catalog,
  accounts = [],
  transactions = [],
  onRevoke,
  busy,
}) {
  const [open, setOpen] = useState(false);
  const status = connection.status.toLowerCase();
  const canRevoke = connection.status === "GRANTED";
  const ids = new Set(connection.accountIds);
  const sampleAccount = accounts.find((a) => ids.has(a.accountId));
  const sampleTxn = transactions.find((t) => ids.has(t.accountId));

  return (
    <div className={`card connection ${status} ${open ? "open" : ""}`}>
      <div className="conn-head">
        <button
          type="button"
          className="conn-toggle"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="conn-caret" aria-hidden="true">
            {open ? "▾" : "▸"}
          </span>
          <span className="conn-title">
            <strong>{connection.sourceLabel}</strong>
            <span className={`badge status-${status}`}>{connection.status}</span>
          </span>
          <span className="conn-sub">
            {expiryLabel(connection)} · {connection.accountIds.length} account
            {connection.accountIds.length === 1 ? "" : "s"}
          </span>
        </button>
        {canRevoke ? (
          <ConfirmButton
            label="Revoke"
            confirmLabel={`Confirm — revoke ${connection.sourceLabel}`}
            onConfirm={() => onRevoke(connection.connectionId)}
            busy={busy}
          />
        ) : (
          <button type="button" className="btn-revoke" disabled>
            Access ended
          </button>
        )}
      </div>

      <div className="scopes">
        {connection.scopes.map((scope) => (
          <ScopeChip key={scope} scope={scope} catalog={catalog} />
        ))}
      </div>

      {open && (
        <div className="conn-detail">
          <div className="conn-detail-col">
            <h4>What {connection.sourceLabel} can access</h4>
            <ul className="access-list">
              {connection.scopes.map((scope) => (
                <li key={scope}>
                  <span className="ok-tick" aria-hidden="true">
                    ✓
                  </span>
                  {catalog?.[scope]?.label || scope}
                </li>
              ))}
            </ul>
            {sampleAccount ? (
              <table className="sample-table">
                <tbody>
                  <tr>
                    <td>Account</td>
                    <td>{sampleAccount.nickname || sampleAccount.accountType}</td>
                  </tr>
                  <tr>
                    <td>Type</td>
                    <td>{sampleAccount.accountType}</td>
                  </tr>
                  {sampleAccount.maskedNumber && (
                    <tr>
                      <td>Masked no.</td>
                      <td>{sampleAccount.maskedNumber}</td>
                    </tr>
                  )}
                  <tr>
                    <td>Currency</td>
                    <td>{sampleAccount.currency}</td>
                  </tr>
                  {sampleAccount.balanceShared && sampleAccount.current != null ? (
                    <tr>
                      <td>Balance</td>
                      <td>{formatMoney(sampleAccount.current, sampleAccount.currency)}</td>
                    </tr>
                  ) : (
                    <tr>
                      <td>Balance</td>
                      <td className="withheld">not shared</td>
                    </tr>
                  )}
                </tbody>
              </table>
            ) : (
              <p className="muted">No data is being shared.</p>
            )}
          </div>

          <div className="conn-detail-col">
            <h4>Sample transaction</h4>
            {sampleTxn ? (
              <dl className="sample-txn">
                <div>
                  <dt>Date</dt>
                  <dd>{formatDateTime(sampleTxn.occurredAt)}</dd>
                </div>
                <div>
                  <dt>Description</dt>
                  <dd>{sampleTxn.description || "—"}</dd>
                </div>
                <div>
                  <dt>Amount</dt>
                  <dd>{formatMoney(sampleTxn.amount, sampleTxn.currency)}</dd>
                </div>
                <div>
                  <dt>Category</dt>
                  <dd>{sampleTxn.category || "—"}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{sampleTxn.status}</dd>
                </div>
              </dl>
            ) : (
              <p className="muted">No transactions shared under this connection.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
