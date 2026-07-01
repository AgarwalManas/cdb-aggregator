import { formatMoney } from "../format.js";

// Household net worth, computed server-side from consented balances only.
export default function NetWorthPanel({ netWorth }) {
  if (!netWorth) return null;
  const { currency, assets, liabilities, netWorth: total, memberName, excluded } = netWorth;

  return (
    <div className="card networth">
      <div className="nw-head">
        <span className="muted">Household net worth · {memberName}</span>
        <h2 className="nw-total">{formatMoney(total, currency)}</h2>
      </div>
      <div className="nw-split">
        <div>
          <span className="muted">Assets</span>
          <strong className="pos">{formatMoney(assets, currency)}</strong>
        </div>
        <div>
          <span className="muted">Liabilities</span>
          <strong className="neg">{formatMoney(liabilities, currency)}</strong>
        </div>
      </div>
      {excluded.length > 0 && (
        <p className="nw-excluded">
          {excluded.length} account{excluded.length === 1 ? "" : "s"} not counted —{" "}
          {excluded.map((e) => e.sourceLabel).join(", ")} didn&apos;t share a balance.
        </p>
      )}
    </div>
  );
}
