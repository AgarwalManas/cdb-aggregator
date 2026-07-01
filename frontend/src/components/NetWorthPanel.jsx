import { formatMoney } from "../format.js";

// Household net worth, computed server-side from consented balances only.
//
// The signature of the whole project (item-19): minimization made *visible*. The
// composition bar shows each counted asset proportionally, and every balance the
// gate withheld appears as an explicit dashed gap — plus a named "withheld" row
// with its reason. The excluded balance isn't silently dropped; you can see it
// being kept out of your total, for you.
export default function NetWorthPanel({ netWorth }) {
  if (!netWorth) return null;
  const { currency, assets, liabilities, netWorth: total, memberName, included, excluded } =
    netWorth;

  const assetLines = included.filter((l) => l.balanceType === "ASSET");

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

      <div
        className="nw-bar"
        role="img"
        aria-label="Asset composition by account; withheld balances shown as dashed gaps"
      >
        {assetLines.map((l, i) => (
          <div
            key={l.accountId}
            className="nw-seg"
            style={{ flexGrow: Number(l.current), opacity: 1 - (i % 4) * 0.16 }}
            title={`${l.sourceLabel}: ${formatMoney(l.current, currency)}`}
          />
        ))}
        {excluded.map((e) => (
          <div
            key={e.accountId}
            className="nw-seg nw-seg-withheld"
            title={`${e.sourceLabel}: ${e.reason}`}
          />
        ))}
      </div>

      {excluded.length > 0 && (
        <div className="nw-withheld">
          <span className="lead">Withheld from this total — the gate working for you:</span>
          <ul>
            {excluded.map((e) => (
              <li key={e.accountId}>
                <span className="src">{e.sourceLabel}</span>
                <span className="tag">balance not shared · excluded</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
