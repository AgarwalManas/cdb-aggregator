import { formatDate, formatMoney } from "../format.js";

// The merged, most-recent-first transaction feed across all sources.
export default function TransactionsFeed({ transactions }) {
  if (!transactions.length) return <p className="empty">No transactions to show.</p>;

  return (
    <div className="card feed">
      {transactions.map((t) => {
        const credit = t.direction === "CREDIT";
        return (
          <div key={`${t.accountId}:${t.transactionId}`} className="txn-row">
            <div className="txn-main">
              <strong>{t.description || "Transaction"}</strong>
              <span className="muted txn-sub">
                {t.sourceLabel}
                {t.category ? ` · ${t.category}` : ""} · {formatDate(t.occurredAt)}
                {t.status === "PENDING" ? " · pending" : ""}
              </span>
            </div>
            <span className={`amount ${credit ? "pos" : "neg"}`}>
              {credit ? "+" : "−"}
              {formatMoney(t.amount, t.currency)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
