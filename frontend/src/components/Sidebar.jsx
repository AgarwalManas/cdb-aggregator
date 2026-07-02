import Icon from "./Icon.jsx";

// The app shell's left navigation (slice 1 of the layout refactor): a grouped
// sidebar — the product, then the clearly-quarantined "Explore (Demo)" frontier
// features, then the "Trust & Privacy" explainers. Collapsible to an icon-only
// rail; labels come back as tooltips.
export default function Sidebar({ pages, groups, active, onNavigate, collapsed, onToggleCollapse }) {
  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
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
                    title={collapsed ? pages[key].label : undefined}
                    onClick={() => onNavigate(key)}
                  >
                    <Icon name={pages[key].icon} className="nav-ico" />
                    <span className="nav-label">{pages[key].label}</span>
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
          className="collapse-btn"
          onClick={onToggleCollapse}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <Icon name={collapsed ? "chevronsRight" : "chevronsLeft"} />
          <span className="nav-label">Collapse</span>
        </button>
      </div>
    </aside>
  );
}
