import { useEffect, useState } from "react";

import { getAccounts, getNetWorth, getTransactions } from "../api.js";
import AccountsList from "../components/AccountsList.jsx";
import NetWorthPanel from "../components/NetWorthPanel.jsx";
import { SkeletonCard } from "../components/Skeleton.jsx";
import TransactionsFeed from "../components/TransactionsFeed.jsx";

// The unified client view (Item 10): net worth, merged accounts, merged feed.
// Every number here came through the consent gate.
export default function OverviewPage() {
  const [netWorth, setNetWorth] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [nw, accts, txns] = await Promise.all([
          getNetWorth(),
          getAccounts(),
          getTransactions(),
        ]);
        setNetWorth(nw);
        setAccounts(accts);
        setTransactions(txns);
      } catch (err) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (error) return <div className="error">{error}</div>;

  if (loading) {
    return (
      <>
        <section>
          <SkeletonCard lines={4} />
        </section>
        <div className="overview-cols">
          <section>
            <h2>Accounts</h2>
            <SkeletonCard lines={5} />
          </section>
          <section>
            <h2>Recent activity</h2>
            <SkeletonCard lines={5} />
          </section>
        </div>
      </>
    );
  }

  return (
    <>
      <section>
        <NetWorthPanel netWorth={netWorth} />
      </section>

      <div className="overview-cols">
        <section>
          <h2>Accounts</h2>
          <AccountsList accounts={accounts} />
        </section>

        <section>
          <h2>Recent activity</h2>
          <TransactionsFeed transactions={transactions} />
        </section>
      </div>

      <p className="section-note gate-note">
        Everything above is read through your consent — connections you haven&apos;t authorized, or
        balances you didn&apos;t share, never appear here.
      </p>
    </>
  );
}
