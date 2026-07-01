import { formatMoney } from "../format.js";

const TYPE_LABEL = {
  CHECKING: "Chequing",
  SAVINGS: "Savings",
  TFSA: "TFSA",
  RRSP: "RRSP",
  BROKERAGE: "Brokerage",
  CREDIT_CARD: "Credit card",
  MORTGAGE: "Mortgage",
  LINE_OF_CREDIT: "Line of credit",
};

function Balance({ account }) {
  if (!account.balanceShared) {
    return <span className="badge status-expired">Balance not shared</span>;
  }
  const isLiability = account.balanceType === "LIABILITY";
  return (
    <span className={`amount ${isLiability ? "neg" : "pos"}`}>
      {isLiability ? "−" : ""}
      {formatMoney(account.current, account.currency)}
    </span>
  );
}

// Merged accounts across every connected source, grouped by source.
export default function AccountsList({ accounts }) {
  if (!accounts.length) return <p className="empty">No accounts to show.</p>;

  const bySource = {};
  for (const a of accounts) {
    (bySource[a.sourceLabel] ||= []).push(a);
  }

  return (
    <div className="accounts">
      {Object.entries(bySource).map(([source, items]) => (
        <div key={source} className="card source-group">
          <h3 className="source-name">{source}</h3>
          {items.map((a) => (
            <div key={a.accountId} className="account-row">
              <div>
                <strong>{a.nickname || TYPE_LABEL[a.accountType] || a.accountType}</strong>
                <span className="muted account-sub">
                  {TYPE_LABEL[a.accountType] || a.accountType}
                  {a.maskedNumber ? ` · ${a.maskedNumber}` : ""}
                </span>
              </div>
              <Balance account={a} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
