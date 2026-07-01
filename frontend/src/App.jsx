import { useEffect, useState } from "react";

import { getScopes } from "./api.js";
import ConsentPage from "./pages/ConsentPage.jsx";
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
};

export default function App() {
  const [tab, setTab] = useState("overview");
  const [scopeCatalog, setScopeCatalog] = useState({});

  useEffect(() => {
    getScopes()
      .then((list) => setScopeCatalog(Object.fromEntries(list.map((s) => [s.scope, s]))))
      .catch(() => setScopeCatalog({}));
  }, []);

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>{TABS[tab].title}</h1>
          <p className="subtitle">{TABS[tab].subtitle}</p>
        </div>
        <div className="who">
          <span className="avatar">AL</span>
          <div>
            <strong>Ada Lovelace</strong>
            <span className="muted">Household</span>
          </div>
        </div>
      </header>

      <nav className="tabs">
        <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>
          Overview
        </button>
        <button className={tab === "consent" ? "active" : ""} onClick={() => setTab("consent")}>
          Consent &amp; Traceability
        </button>
      </nav>

      {tab === "overview" ? <OverviewPage /> : <ConsentPage scopeCatalog={scopeCatalog} />}

      <footer className="foot">cdb-aggregator · FDX-aligned consent &amp; traceability demo</footer>
    </div>
  );
}
