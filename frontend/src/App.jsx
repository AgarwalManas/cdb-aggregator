import { useEffect, useState } from "react";

import { getScopes, resetDemo } from "./api.js";
import { CHAT_STORAGE_KEY } from "./components/AssistantChat.jsx";
import Sidebar from "./components/Sidebar.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import AddressPage from "./pages/AddressPage.jsx";
import AgentPage from "./pages/AgentPage.jsx";
import ComparePage from "./pages/ComparePage.jsx";
import ConsentPage from "./pages/ConsentPage.jsx";
import CredentialsPage from "./pages/CredentialsPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import HowItWorksPage from "./pages/HowItWorksPage.jsx";
import OverviewPage from "./pages/OverviewPage.jsx";
import WhySaferPage from "./pages/WhySaferPage.jsx";

// Each page: its sidebar group, nav label + icon, and the header title/subtitle.
const PAGES = {
  dashboard: {
    group: "main",
    label: "Dashboard",
    icon: "grid",
    title: "Dashboard",
    subtitle: "Your data-sharing at a glance — connections, consents, and recent access.",
  },
  accounts: {
    group: "main",
    label: "Bank Accounts",
    icon: "bank",
    title: "Bank Accounts",
    subtitle: "Everything in one place — shown only with your consent.",
  },
  control: {
    group: "main",
    label: "Control Centre",
    icon: "shield",
    title: "Control Centre",
    subtitle: "Decide what's shared, for how long, and see every access.",
  },
  assistant: {
    group: "main",
    label: "Assistant",
    icon: "sparkle",
    title: "Assistant",
    subtitle: "Ask, delegate, and decide in one conversation — it suggests, it never acts.",
  },
  address: {
    group: "explore",
    label: "Portable Address",
    icon: "at",
    title: "Portable Address",
    subtitle:
      "A bank-neutral handle you own — resolved to a one-time routing token, never your bank, branch, or account number.",
  },
  credentials: {
    group: "explore",
    label: "Credentials",
    icon: "badge",
    title: "Credentials & proofs",
    subtitle: "Prove a fact, hold it in a wallet, present it to a verifier — a simulation.",
  },
  howitworks: {
    group: "trust",
    label: "How it works",
    icon: "target",
    title: "How it works",
    subtitle: "CDB Aggregator puts you in control of your data, every step of the way.",
  },
  safer: {
    group: "trust",
    label: "Why this is safer",
    icon: "shieldCheck",
    title: "Why this is safer",
    subtitle: "Designed around privacy, transparency, and your control — not convenience.",
  },
  compare: {
    group: "trust",
    label: "Old vs New",
    icon: "clock",
    title: "Old vs New",
    subtitle: "A better way to share data — privacy-first, consent-driven, always in your control.",
  },
};

// Sidebar groups, in order.
const GROUPS = [
  { key: "main", heading: null, items: ["dashboard", "accounts", "control", "assistant"] },
  { key: "explore", heading: "Explore (Demo)", items: ["address", "credentials"] },
  { key: "trust", heading: "Trust & Privacy", items: ["howitworks", "safer", "compare"] },
];

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [scopeCatalog, setScopeCatalog] = useState({});
  const [resetting, setResetting] = useState(false);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("cdb-sidebar") === "collapsed",
  );

  useEffect(() => {
    getScopes()
      .then((list) => setScopeCatalog(Object.fromEntries(list.map((s) => [s.scope, s]))))
      .catch(() => setScopeCatalog({}));
  }, []);

  function toggleCollapsed() {
    setCollapsed((v) => {
      localStorage.setItem("cdb-sidebar", v ? "expanded" : "collapsed");
      return !v;
    });
  }

  async function handleReset() {
    setResetting(true);
    try {
      await resetDemo();
      sessionStorage.removeItem(CHAT_STORAGE_KEY); // the assistant chat restarts too
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
        collapsed={collapsed}
        onToggleCollapse={toggleCollapsed}
      />

      <div className="main">
        <div className="main-inner">
          <header className="topbar">
            <div className="page-head" key={page}>
              <h1>{meta.title}</h1>
              <p className="subtitle">{meta.subtitle}</p>
            </div>
            <div className="topbar-right">
              <span className="demo-pill">Demo data</span>
              <button
                type="button"
                className="reset-demo"
                onClick={handleReset}
                disabled={resetting}
                title="Restore the demo to its seeded state. Only affects your session."
              >
                {resetting ? "Resetting…" : "Reset demo"}
              </button>
              <ThemeToggle />
              <div className="who">
                <span className="avatar">AL</span>
                <div>
                  <strong>Ada Lovelace</strong>
                  <span className="muted">Household</span>
                </div>
              </div>
            </div>
          </header>

          <div className="page" key={`page-${page}`}>
            {page === "dashboard" && <DashboardPage onNavigate={setPage} />}
            {page === "accounts" && <OverviewPage />}
            {page === "control" && <ConsentPage scopeCatalog={scopeCatalog} />}
            {page === "assistant" && <AgentPage scopeCatalog={scopeCatalog} />}
            {page === "address" && <AddressPage />}
            {page === "credentials" && <CredentialsPage />}
            {page === "howitworks" && <HowItWorksPage onNavigate={setPage} />}
            {page === "safer" && <WhySaferPage onNavigate={setPage} />}
            {page === "compare" && <ComparePage />}
          </div>

          <footer className="foot">
            cdb-aggregator · FDX-aligned consent &amp; traceability demo
          </footer>
        </div>
      </div>
    </div>
  );
}
