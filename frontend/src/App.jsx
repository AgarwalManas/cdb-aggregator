import { useEffect, useState } from "react";

import { getScopes, resetDemo } from "./api.js";
import ThemeToggle from "./components/ThemeToggle.jsx";
import AddressPage from "./pages/AddressPage.jsx";
import AgentPage from "./pages/AgentPage.jsx";
import ComparePage from "./pages/ComparePage.jsx";
import ConsentPage from "./pages/ConsentPage.jsx";
import CredentialsPage from "./pages/CredentialsPage.jsx";
import OverviewPage from "./pages/OverviewPage.jsx";

const TABS = {
  overview: {
    title: "Your finances",
    subtitle: "Everything in one place — shown only with your consent.",
  },
  consent: {
    title: "Consent & Traceability",
    subtitle: "Choose exactly who can see your financial data — and revoke it anytime.",
  },
  assistant: {
    title: "Assistant",
    subtitle: "Delegate a scoped, revocable task to an agent — it suggests, it never acts.",
  },
  compare: {
    title: "Old way vs new way",
    subtitle: "Why token-based FDX access beats credential-based screen-scraping.",
  },
  address: {
    title: "Portable address",
    subtitle: "A bank-neutral handle you own — resolved to a one-time token, never your account.",
  },
  credentials: {
    title: "Credentials & proofs",
    subtitle: "Prove a fact, hold it in a wallet, present it to a verifier — a simulation.",
  },
};

// Tab order and the (shorter) labels shown in the nav.
const NAV = [
  ["overview", "Overview"],
  ["consent", "Consent & Traceability"],
  ["assistant", "Assistant"],
  ["compare", "Old vs New"],
  ["address", "Portable address"],
  ["credentials", "Credentials"],
];

export default function App() {
  const [tab, setTab] = useState("overview");
  const [scopeCatalog, setScopeCatalog] = useState({});
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    getScopes()
      .then((list) => setScopeCatalog(Object.fromEntries(list.map((s) => [s.scope, s]))))
      .catch(() => setScopeCatalog({}));
  }, []);

  async function handleReset() {
    setResetting(true);
    try {
      await resetDemo();
      window.location.reload(); // refetch every tab from the freshly-seeded world
    } catch {
      setResetting(false);
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>{TABS[tab].title}</h1>
          <p className="subtitle">{TABS[tab].subtitle}</p>
        </div>
        <div className="topbar-right">
          <ThemeToggle />
          <button
            className="reset-demo"
            onClick={handleReset}
            disabled={resetting}
            title="Restore the demo to its seeded state. Only affects your session."
          >
            {resetting ? "Resetting…" : "Reset demo"}
          </button>
          <div className="who">
            <span className="avatar">AL</span>
            <div>
              <strong>Ada Lovelace</strong>
              <span className="muted">Household</span>
            </div>
          </div>
        </div>
      </header>

      <nav className="tabs" aria-label="Views">
        {NAV.map(([key, label]) => (
          <button
            key={key}
            className={tab === key ? "active" : ""}
            aria-current={tab === key ? "page" : undefined}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "overview" && <OverviewPage />}
      {tab === "consent" && <ConsentPage scopeCatalog={scopeCatalog} />}
      {tab === "assistant" && <AgentPage scopeCatalog={scopeCatalog} />}
      {tab === "compare" && <ComparePage />}
      {tab === "address" && <AddressPage />}
      {tab === "credentials" && <CredentialsPage />}

      <footer className="foot">cdb-aggregator · FDX-aligned consent &amp; traceability demo</footer>
    </div>
  );
}
