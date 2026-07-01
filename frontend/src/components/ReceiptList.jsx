import { useState } from "react";

import { formatDateTime } from "../format.js";

// Access receipts (item-29): each audit event as a consumer-legible receipt —
// who accessed what cluster, under which grant, for what purpose, disclosed vs
// withheld — expandable to detail, with a machine-readable JSON export.
function downloadReceipt(receipt) {
  const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${receipt.receiptId}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReceiptList({ receipts }) {
  const [openId, setOpenId] = useState(null);
  if (!receipts) return null;
  if (receipts.length === 0) return <p className="empty">No access recorded yet.</p>;

  return (
    <ul className="receipt-scroll">
      {receipts.map((r) => {
        const open = openId === r.receiptId;
        return (
          <li key={r.receiptId} className={`receipt ${r.allowed ? "" : "refused"}`}>
            <button
              type="button"
              className="receipt-head"
              aria-expanded={open}
              onClick={() => setOpenId(open ? null : r.receiptId)}
            >
              <span className={`accessor-dot ${r.accessorType}`} aria-hidden="true" />
              <span className="receipt-main">
                <span className="receipt-line">
                  <strong>{r.accessorLabel}</strong> · {r.purpose}
                </span>
                <span className="receipt-sub">
                  {r.clusterLabel} · {formatDateTime(r.occurredAt)}
                </span>
              </span>
              <span className={`badge status-${r.allowed ? "granted" : "revoked"}`}>
                {r.allowed ? "Disclosed" : "Refused"}
              </span>
            </button>
            {open && (
              <div className="receipt-detail">
                <p className="receipt-why">{r.why}</p>
                <dl className="authority-meta">
                  <div>
                    <dt>Fields in this cluster</dt>
                    <dd>{r.fields.join(", ") || "—"}</dd>
                  </div>
                  <div>
                    <dt>Account</dt>
                    <dd>{r.accountId || "—"}</dd>
                  </div>
                  <div>
                    <dt>Authorizing grant</dt>
                    <dd>
                      <code>{r.authorizingConsentId || "—"}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Disclosed</dt>
                    <dd>
                      {r.allowed ? `${r.recordCount} record${r.recordCount === 1 ? "" : "s"}` : "nothing"}
                    </dd>
                  </div>
                  {r.withheld.length > 0 && (
                    <div>
                      <dt>Withheld</dt>
                      <dd>{r.withheld.join(", ")}</dd>
                    </div>
                  )}
                </dl>
                <button type="button" className="btn-revoke" onClick={() => downloadReceipt(r)}>
                  Download JSON
                </button>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
