import { useState } from "react";

import Icon from "./Icon.jsx";

// The app shell's left navigation: a grouped sidebar — the product, then the
// clearly-quarantined "Explore (Demo)" frontier features, then the "Trust &
// Privacy" explainers. The header row carries search and the collapse toggle
// (Claude-style); collapsed, it becomes an icon-only rail with tooltips.
export default function Sidebar({ pages, groups, active, onNavigate, collapsed, onToggleCollapse }) {
  const [searching, setSearching] = useState(false);
  const [query, setQuery] = useState("");

  const openSearch = () => {
    if (collapsed) onToggleCollapse();
    setSearching(true);
  };
  const closeSearch = () => {
    setSearching(false);
    setQuery("");
  };

  const q = query.trim().toLowerCase();
  const matches = searching && q
    ? Object.keys(pages).filter((key) => {
        const p = pages[key];
        return `${p.label} ${p.title} ${p.subtitle}`.toLowerCase().includes(q);
      })
    : null;

  const go = (key) => {
    onNavigate(key);
    closeSearch();
  };

  const item = (key) => (
    <li key={key}>
      <button
        type="button"
        className={`nav-item ${active === key ? "active" : ""}`}
        aria-current={active === key ? "page" : undefined}
        title={collapsed ? pages[key].label : undefined}
        onClick={() => go(key)}
      >
        <Icon name={pages[key].icon} className="nav-ico" />
        <span className="nav-label">{pages[key].label}</span>
      </button>
    </li>
  );

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <span className="brand-name">CDB Aggregator</span>
        <span className="brand-actions">
          <button
            type="button"
            className="brand-btn"
            title="Search pages"
            aria-label="Search pages"
            onClick={searching ? closeSearch : openSearch}
          >
            <Icon name="search" />
          </button>
          <button
            type="button"
            className="brand-btn"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={onToggleCollapse}
          >
            <Icon name="panel" />
          </button>
        </span>
      </div>

      {searching && !collapsed && (
        <div className="nav-search">
          <Icon name="search" />
          <input
            autoFocus
            value={query}
            placeholder="Search pages…"
            aria-label="Search pages"
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") closeSearch();
              if (e.key === "Enter" && matches?.length) go(matches[0]);
            }}
          />
        </div>
      )}

      <nav className="side-nav" aria-label="Sections">
        {matches ? (
          <div className="nav-group">
            <p className="nav-heading">Results</p>
            {matches.length ? (
              <ul>{matches.map(item)}</ul>
            ) : (
              <p className="nav-empty">No pages match.</p>
            )}
          </div>
        ) : (
          groups.map((group) => (
            <div className="nav-group" key={group.key}>
              {group.heading && <p className="nav-heading">{group.heading}</p>}
              <ul>{group.items.map(item)}</ul>
            </div>
          ))
        )}
      </nav>
    </aside>
  );
}
