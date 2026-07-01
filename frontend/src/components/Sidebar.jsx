import ThemeToggle from "./ThemeToggle.jsx";

// The app shell's left navigation (slice 1 of the layout refactor): a grouped
// sidebar — the product, then the clearly-quarantined "Explore (Demo)" frontier
// features, then "How it works" explainers.
export default function Sidebar({ pages, groups, active, onNavigate, onReset, resetting }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-name">CDB Aggregator</span>
      </div>

      <nav className="side-nav" aria-label="Sections">
        {groups.map((group) => (
          <div className="nav-group" key={group.key}>
            {group.heading && <p className="nav-heading">{group.heading}</p>}
            <ul>
              {group.items.map((key) => (
                <li key={key}>
                  <button
                    type="button"
                    className={`nav-item ${active === key ? "active" : ""}`}
                    aria-current={active === key ? "page" : undefined}
                    onClick={() => onNavigate(key)}
                  >
                    <span>{pages[key].label}</span>
                    {group.key === "explore" && <span className="nav-tag">Demo</span>}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="side-foot">
        <button
          type="button"
          className="reset-demo"
          onClick={onReset}
          disabled={resetting}
          title="Restore the demo to its seeded state. Only affects your session."
        >
          {resetting ? "Resetting…" : "Reset demo"}
        </button>
        <ThemeToggle />
      </div>
    </aside>
  );
}
