import { useEffect, useMemo, useRef, useState } from "react";

import { formatDateTime } from "../format.js";

// Activity Log (slice 5.2): one table merging the audit trail and the access
// receipts. A date-range filter, a single Filters popover exposing every column,
// free-text search, tick-to-select, expandable full receipts, and multi-format
// export (per-row and for the selection) with a proper letterhead PDF.

const COLUMNS = [
  "Receipt",
  "When",
  "By",
  "Action",
  "Scope",
  "Account",
  "Decision",
  "Disclosed",
  "Withheld",
  "Grant",
];

const DAY = 86400000;
const DATE_PRESETS = [
  ["all", "All time", () => null],
  ["day", "Last day", (now) => now - DAY],
  ["week", "Last week", (now) => now - 7 * DAY],
  ["month", "Last month", (now) => now - 30 * DAY],
  ["3m", "Last 3 months", (now) => now - 91 * DAY],
  ["6m", "Last 6 months", (now) => now - 182 * DAY],
  ["12m", "Last 12 months", (now) => now - 365 * DAY],
  ["ytd", "Year to date", (now) => new Date(new Date(now).getFullYear(), 0, 1).getTime()],
];

const FILTER_FIELDS = [
  ["by", "By", (r) => r.accessorLabel],
  ["action", "Action", (r) => r.purpose],
  ["scope", "Scope", (r) => r.clusterLabel],
  ["account", "Account", (r) => r.accountId],
  ["decision", "Decision", (r) => (r.allowed ? "Allowed" : "Denied")],
  ["grant", "Grant", (r) => r.authorizingConsentId],
];

const EXPORT_OPTS = [
  ["Markdown (.md)", "md"],
  ["CSV (.csv)", "csv"],
  ["JSON (.json)", "json"],
  ["PDF (.pdf)", "pdf"],
];

function summaryRow(r) {
  return {
    Receipt: r.receiptId,
    When: r.occurredAt,
    By: r.accessorLabel,
    Action: r.purpose,
    Scope: r.clusterLabel,
    Account: r.accountId || "—",
    Decision: r.allowed ? "ALLOWED" : "DENIED",
    Disclosed: r.allowed ? String(r.recordCount) : "0",
    Withheld: r.withheld.join("; ") || "—",
    Grant: r.authorizingConsentId || "—",
  };
}

const download = (name, text, mime) => {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
};

const csvCell = (v) => `"${String(v).replace(/"/g, '""')}"`;
const mdCell = (v) => String(v).replace(/\|/g, "\\|");
const esc = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function toJSON(rows, enhanced) {
  return JSON.stringify(rows.map((r) => (enhanced ? r : summaryRow(r))), null, 2);
}
function toCSV(rows, enhanced) {
  const cols = enhanced ? [...COLUMNS, "Fields", "Why"] : COLUMNS;
  const header = cols.map(csvCell).join(",");
  const lines = rows.map((r) => {
    const s = summaryRow(r);
    const base = COLUMNS.map((c) => csvCell(s[c]));
    if (enhanced) base.push(csvCell(r.fields.join("; ")), csvCell(r.why));
    return base.join(",");
  });
  return [header, ...lines].join("\n");
}
function toMarkdown(rows, enhanced) {
  const header = `| ${COLUMNS.join(" | ")} |`;
  const rule = `| ${COLUMNS.map(() => "---").join(" | ")} |`;
  const body = rows.map((r) => `| ${COLUMNS.map((c) => mdCell(summaryRow(r)[c])).join(" | ")} |`);
  let out = [header, rule, ...body].join("\n");
  if (enhanced) {
    out +=
      "\n\n## Receipt details\n\n" +
      rows
        .map((r) => `- **${r.receiptId}** — ${mdCell(r.why)} _(fields: ${r.fields.join(", ")})_`)
        .join("\n");
  }
  return out;
}

function printPdf(rows, enhanced, meta) {
  const win = window.open("", "_blank");
  if (!win) return;
  const head = COLUMNS.map((c) => `<th>${c}</th>`).join("");
  const body = rows
    .map((r) => {
      const s = summaryRow(r);
      const cells = COLUMNS.map((c) => `<td>${esc(s[c])}</td>`).join("");
      const detail = enhanced
        ? `<tr class="d"><td colspan="${COLUMNS.length}"><b>Accessor:</b> ${esc(r.accessor)} &nbsp; <b>Why:</b> ${esc(r.why)} &nbsp; <b>Fields:</b> ${esc(r.fields.join(", "))}</td></tr>`
        : "";
      return `<tr>${cells}</tr>${detail}`;
    })
    .join("");
  const single = rows.length === 1 ? rows[0] : null;
  const accounts = [...new Set(rows.map((r) => r.accountId).filter(Boolean))];
  const metaRows = [
    ["Account holder", meta.holder],
    ["Generated", meta.generated],
    ["Records", String(rows.length)],
    single ? ["Receipt", single.receiptId] : null,
    single ? ["Account", single.accountId || "—"] : ["Accounts", accounts.join(", ") || "—"],
  ]
    .filter(Boolean)
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`)
    .join("");
  win.document.write(
    `<html><head><title>CDB Aggregator — access log</title><style>
      body{font-family:system-ui,-apple-system,sans-serif;color:#1a1f2b;padding:40px;font-size:12px}
      .lh{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:2px solid #10695C;padding-bottom:12px;margin-bottom:16px}
      .brand{font-size:20px;font-weight:700;font-family:ui-monospace,monospace;color:#10695C}
      .doc{font-size:13px;color:#555}
      table.meta{border-collapse:collapse;margin-bottom:18px;font-size:12px}
      table.meta td{padding:2px 22px 2px 0}
      table.meta td:first-child{color:#888}
      table.log{border-collapse:collapse;width:100%}
      table.log th,table.log td{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top}
      table.log th{background:#f4f6f8;font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:#555}
      tr.d td{background:#fafbfc;font-size:11px;color:#444}
      .foot{margin-top:20px;font-size:10px;color:#999}
    </style></head><body>
      <div class="lh"><div class="brand">CDB Aggregator</div><div class="doc">Access log — receipts</div></div>
      <table class="meta">${metaRows}</table>
      <table class="log"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
      <div class="foot">FDX-aligned consent &amp; traceability demo · Demo data — not a statement of live regulatory integration.</div>
    </body></html>`,
  );
  win.document.close();
  win.focus();
  win.print();
}

function runExport(kind, rows, enhanced, meta) {
  if (kind === "md") download("access-log.md", toMarkdown(rows, enhanced), "text/markdown");
  else if (kind === "csv") download("access-log.csv", toCSV(rows, enhanced), "text/csv");
  else if (kind === "json") download("access-log.json", toJSON(rows, enhanced), "application/json");
  else printPdf(rows, enhanced, meta);
}

const distinct = (rows, get) =>
  Array.from(new Set(rows.map(get).filter((v) => v != null && v !== ""))).sort();

export default function ActivityLog({ receipts, holder = "Ada Lovelace" }) {
  const [range, setRange] = useState("all");
  const [filters, setFilters] = useState({});
  const [query, setQuery] = useState("");
  const [sortDir, setSortDir] = useState("desc");
  const [selected, setSelected] = useState(() => new Set());
  const [openId, setOpenId] = useState(null);
  const [enhanced, setEnhanced] = useState(true);
  const [menu, setMenu] = useState(null); // "date" | "filters" | "export" | `row:<id>` | null
  const rootRef = useRef(null);

  useEffect(() => {
    if (!menu) return undefined;
    const onDown = (e) => {
      if (!e.target.closest(".js-menu")) setMenu(null);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menu]);

  const options = useMemo(() => {
    const rows = receipts || [];
    return Object.fromEntries(FILTER_FIELDS.map(([key, , get]) => [key, distinct(rows, get)]));
  }, [receipts]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const now = Date.now();
    const cutoff = (DATE_PRESETS.find((p) => p[0] === range) || DATE_PRESETS[0])[2](now);
    const rows = (receipts || []).filter((r) => {
      if (cutoff != null && new Date(r.occurredAt).getTime() < cutoff) return false;
      for (const [key, , get] of FILTER_FIELDS) {
        if (filters[key] && filters[key] !== "all" && String(get(r)) !== filters[key]) return false;
      }
      if (q) {
        const hay = [r.purpose, r.accessorLabel, r.clusterLabel, r.accountId, r.why, r.authorizingConsentId]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    const dir = sortDir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) =>
      a.occurredAt < b.occurredAt ? -dir : a.occurredAt > b.occurredAt ? dir : 0,
    );
  }, [receipts, range, filters, query, sortDir]);

  if (!receipts) return null;

  const meta = { holder, generated: new Date().toLocaleString() };
  const exportRows = selected.size ? visible.filter((r) => selected.has(r.receiptId)) : visible;
  const allSelected = visible.length > 0 && visible.every((r) => selected.has(r.receiptId));
  const activeFilters = FILTER_FIELDS.filter(([k]) => filters[k] && filters[k] !== "all").length;
  const rangeLabel = (DATE_PRESETS.find((p) => p[0] === range) || DATE_PRESETS[0])[1];

  const toggleAll = () =>
    setSelected((prev) =>
      visible.every((r) => prev.has(r.receiptId))
        ? new Set()
        : new Set(visible.map((r) => r.receiptId)),
    );
  const toggleOne = (id) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const setFilter = (key, value) => setFilters((f) => ({ ...f, [key]: value }));
  const clearFilters = () => {
    setFilters({});
    setQuery("");
    setRange("all");
  };

  return (
    <div className="log" ref={rootRef}>
      <div className="log-bar">
        <div className="log-controls">
          <div className="js-menu date-wrap">
            <button
              type="button"
              className="filter-btn"
              onClick={() => setMenu(menu === "date" ? null : "date")}
            >
              📅 {rangeLabel} ▾
            </button>
            {menu === "date" && (
              <div className="export-menu date-menu" role="menu">
                <span className="menu-heading">Preset ranges</span>
                {DATE_PRESETS.map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    className={range === key ? "active" : ""}
                    onClick={() => {
                      setRange(key);
                      setMenu(null);
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="js-menu filter-wrap">
            <button
              type="button"
              className="filter-btn"
              onClick={() => setMenu(menu === "filters" ? null : "filters")}
            >
              ⚙ Filters{activeFilters ? ` (${activeFilters})` : ""}
            </button>
            {menu === "filters" && (
              <div className="filter-panel">
                {FILTER_FIELDS.map(([key, label]) => (
                  <label key={key} className="filter-field">
                    <span>{label}</span>
                    <select
                      value={filters[key] || "all"}
                      onChange={(e) => setFilter(key, e.target.value)}
                    >
                      <option value="all">All</option>
                      {(key === "decision" ? ["Allowed", "Denied"] : options[key]).map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
                <button type="button" className="link filter-clear" onClick={() => setFilters({})}>
                  Clear filters
                </button>
              </div>
            )}
          </div>

          <input
            type="search"
            className="log-search"
            placeholder="Search by account, action, scope or grant…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search the log"
          />
        </div>

        <div className="log-export">
          <label className="enhanced-toggle" title="Include full receipt detail in exports">
            <input type="checkbox" checked={enhanced} onChange={() => setEnhanced((v) => !v)} />
            Enhanced download
          </label>
          <div className="js-menu export-wrap">
            <button
              type="button"
              className="btn-primary export-btn"
              onClick={() => setMenu(menu === "export" ? null : "export")}
            >
              ⬆ Export {selected.size ? `(${selected.size})` : `(${visible.length})`} ▾
            </button>
            {menu === "export" && (
              <div className="export-menu" role="menu">
                {EXPORT_OPTS.map(([label, kind]) => (
                  <button
                    key={kind}
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      runExport(kind, exportRows, enhanced, meta);
                      setMenu(null);
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <p className="section-note export-hint">
        {selected.size
          ? `${selected.size} selected for export.`
          : "Tick rows to export a selection, or export everything shown."}{" "}
        Enhanced adds each receipt&apos;s fields and the &ldquo;why&rdquo; line.
      </p>

      {receipts.length === 0 ? (
        <p className="empty">No access recorded yet.</p>
      ) : visible.length === 0 ? (
        <p className="empty">
          No entries match these filters.{" "}
          <button type="button" className="link" onClick={clearFilters}>
            Clear filters
          </button>
          .
        </p>
      ) : (
        <div className="audit-scroll">
          <table className="audit activity-log-table">
            <thead>
              <tr>
                <th className="col-check">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    aria-label="Select all rows"
                  />
                </th>
                <th>
                  <button
                    type="button"
                    className="th-sort"
                    onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
                  >
                    When{" "}
                    <span className="sort-caret" aria-hidden="true">
                      {sortDir === "asc" ? "▲" : "▼"}
                    </span>
                  </button>
                </th>
                <th>By</th>
                <th>Action</th>
                <th>Scope</th>
                <th>Account</th>
                <th>Decision</th>
                <th>Disclosed</th>
                <th>Withheld</th>
                <th>Grant</th>
                <th className="col-caret" aria-label="Details" />
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => (
                <LogRow
                  key={r.receiptId}
                  receipt={r}
                  open={openId === r.receiptId}
                  selected={selected.has(r.receiptId)}
                  enhanced={enhanced}
                  meta={meta}
                  menuOpen={menu === `row:${r.receiptId}`}
                  onMenu={(v) => setMenu(v ? `row:${r.receiptId}` : null)}
                  onToggleSelect={() => toggleOne(r.receiptId)}
                  onToggleOpen={() => setOpenId(openId === r.receiptId ? null : r.receiptId)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function LogRow({ receipt: r, open, selected, enhanced, meta, menuOpen, onMenu, onToggleSelect, onToggleOpen }) {
  const cell = (children, extra = "") => (
    <td className={`row-click ${extra}`} onClick={onToggleOpen}>
      {children}
    </td>
  );
  return (
    <>
      <tr className={`${r.allowed ? "" : "denied"} ${open ? "row-open" : ""}`}>
        <td className="col-check">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggleSelect}
            aria-label={`Select ${r.receiptId}`}
          />
        </td>
        {cell(formatDateTime(r.occurredAt), "muted")}
        {cell(
          r.accessorType === "aggregator" ? (
            <span className="muted">Aggregator</span>
          ) : (
            <span className="by-agent">{r.accessorLabel}</span>
          ),
        )}
        {cell(r.purpose)}
        {cell(r.clusterLabel)}
        {cell(r.accountId || "—", "muted")}
        {cell(
          r.allowed ? (
            <span className="badge status-granted">Allowed</span>
          ) : (
            <span className="badge status-revoked">Denied</span>
          ),
        )}
        {cell(r.allowed ? `${r.recordCount}` : "—", "muted")}
        {cell(r.withheld.length ? r.withheld.join(", ") : "—", "muted withheld-cell")}
        {cell(<code>{r.authorizingConsentId || "—"}</code>, "muted")}
        <td className="col-caret row-click" onClick={onToggleOpen}>
          <span className="row-caret" aria-hidden="true">
            {open ? "▾" : "▸"}
          </span>
        </td>
      </tr>
      {open && (
        <tr className="detail-row">
          <td colSpan={11}>
            <div className="receipt-full">
              <div className="rf-head">
                <span>
                  📄 Receipt <code>{r.receiptId}</code>
                </span>
                <span className="muted">Occurred at {r.occurredAt}</span>
              </div>
              <div className="rf-grid">
                <RfCol
                  items={[
                    ["Accessor", r.accessor],
                    ["Accessor label", r.accessorLabel],
                    ["Accessor type", r.accessorType],
                    ["Purpose", r.purpose],
                  ]}
                />
                <RfCol
                  items={[
                    ["Cluster", r.cluster],
                    ["Cluster label", r.clusterLabel],
                    ["Fields", r.fields.join(", ") || "—"],
                  ]}
                />
                <RfCol
                  items={[
                    ["Account ID", r.accountId || "—"],
                    ["Authorizing grant", r.authorizingConsentId || "—"],
                    ["Allowed", String(r.allowed)],
                    ["Record count", String(r.recordCount)],
                  ]}
                />
                <RfCol
                  items={[
                    ["Withheld", r.withheld.length ? r.withheld.join(", ") : "none"],
                    ["Why", r.why],
                  ]}
                />
              </div>
              <div className="js-menu rf-download">
                <button type="button" className="btn-revoke" onClick={() => onMenu(!menuOpen)}>
                  ⬇ Download ▾
                </button>
                {menuOpen && (
                  <div className="export-menu" role="menu">
                    {EXPORT_OPTS.map(([label, kind]) => (
                      <button
                        key={kind}
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          runExport(kind, [r], enhanced, meta);
                          onMenu(false);
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function RfCol({ items }) {
  return (
    <dl className="rf-col">
      {items.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}
