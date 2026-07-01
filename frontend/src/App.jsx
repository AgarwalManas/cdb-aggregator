import { useEffect, useState } from "react";

import { getScopes, resetDemo } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import AddressPage from "./pages/AddressPage.jsx";
import AgentPage from "./pages/AgentPage.jsx";
import ComparePage from "./pages/ComparePage.jsx";
import ConsentPage from "./pages/ConsentPage.jsx";
import CredentialsPage from "./pages/CredentialsPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import ExplainerPage from "./pages/ExplainerPage.jsx";
import OverviewPage from "./pages/OverviewPage.jsx";

// Each page: its sidebar group, nav label, and the header title/subtitle.
const PAGES = {
  dashboard: {
    group: "main",
    label: "Dashboard",
    title: "Dashboard",
    subtitle: "Your data-sharing at a glance — connections, consents, and recent access.",
  },
  accounts: {
    group: "main",
    label: "Bank Accounts",
    title: "Bank Accounts",
    subtitle: "Everything in one place — shown only with your consent.",
  },
  control: {
    group: "main",
    label: "Control Centre",
    title: "Control Centre",
    subtitle: "Decide what's shared, for how long, and see every access.",
  },
  assistant: {
    group: "main",
    label: "Assistant",
    title: "Assistant",
    subtitle: "Delegate a scoped, revocable task to an agent — it suggests, it never acts.",
  },
  address: {
    group: "explore",
    label: "Portable Address",
    title: "Portable Address",
    subtitle: "A bank-neutral handle you own — resolved to a one-time token, never your account.",
  },
  credentials: {
    group: "explore",
    label: "Credentials",
    title: "Credentials & proofs",
    subtitle: "Prove a fact, hold it in a wallet, present it to a verifier — a simulation.",
  },
  compare: {
    group: "how",
    label: "Old vs New",
    title: "Old way vs new way",
    subtitle: "Why token-based FDX access beats credential-based screen-scraping.",
  },
  safer: {
    group: "how",
    label: "Why this is safer",
    title: "Why this is safer",
    subtitle: "The case for scoped, revocable, token-based access.",
  },
  principles: {
    group: "how",
    label: "Consent principles",
    title: "Consent principles",
    subtitle: "The ideas the whole app is built on.",
  },
};

// Sidebar groups, in order.
const GROUPS = [
  { key: "main", heading: null, items: ["dashboard", "accounts", "control", "assistant"] },
  { key: "explore", heading: "Explore (Demo)", items: ["address", "credentials"] },
  { key: "how", heading: "How it works", items: ["compare", "safer", "principles"] },
];

export default function App() {
  const [page, setPage] = useState("dashboard");
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
      window.location.reload(); // refetch every page from the freshly-seeded world
    } catch {
      setResetting(false);
    }
  }

  const meta = PAGES[page];

  return (
    <div className="app">
      <Sidebar
        pages={PAGES}
        groups={GROUPS}
        active={page}
        onNavigate={setPage}
        onReset={handleReset}
        resetting={resetting}
      />

      <div className="main">
        <div className="main-inner">
          <header className="topbar">
            <div>
              <h1>{meta.title}</h1>
              <p className="subtitle">{meta.subtitle}</p>
            </div>
            <div className="topbar-right">
              <div className="who">
                <span className="avatar">AL</span>
                <div>
                  <strong>Ada Lovelace</strong>
                  <span className="muted">Household</span>
                </div>
              </div>
            </div>
          </header>

          {page === "dashboard" && <DashboardPage onNavigate={setPage} />}
          {page === "accounts" && <OverviewPage />}
          {page === "control" && <ConsentPage scopeCatalog={scopeCatalog} />}
          {page === "assistant" && <AgentPage scopeCatalog={scopeCatalog} />}
          {page === "address" && <AddressPage />}
          {page === "credentials" && <CredentialsPage />}
          {page === "compare" && <ComparePage />}
          {page === "safer" && (
            <ExplainerPage
              title="Why this is safer"
              blurb="The case for scoped, revocable, token-based access over shared credentials."
            />
          )}
          {page === "principles" && (
            <ExplainerPage
              title="Consent principles"
              blurb="Control, Access, Transparency, Traceability, Security — the ideas the app is built on."
            />
          )}

          <footer className="foot">
            cdb-aggregator · FDX-aligned consent &amp; traceability demo
          </footer>
        </div>
      </div>
    </div>
  );
}
